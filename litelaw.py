#!/usr/bin/env python3
import sys
import os
import json
import re
import subprocess
import urllib.request
import urllib.error
import platform
import webbrowser

# --- Configuration ---
# No model is assumed by default -- litelaw doesn't hardcode gemma3:1b or
# anything else as "the" model, since it may not even be installed. Set
# LITEMODEL in the environment, or pass model= explicitly (the web app does
# this from whatever's chosen in Settings).
MODEL = os.environ.get("LITEMODEL", "")
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
AUTO_APPROVE = True  # Set to True to bypass the (y/n) confirmation prompt
MAX_CONTEXT_MESSAGES = 20  # Safeguard to prevent context window bloat
DEFAULT_CONTEXT_SIZE = 2048  # Default num_ctx sent to Ollama; smaller = faster on weak CPUs
OLLAMA_KEEP_ALIVE = "30m"  # Keep the model loaded in RAM between requests to avoid reload latency
_CPU_THREADS = os.cpu_count() or 4

def list_models():
    """Query Ollama's local API for installed model tags. Returns [] if unreachable."""
    try:
        req = urllib.request.Request(OLLAMA_TAGS_URL)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            names = [m.get("name") for m in data.get("models", []) if m.get("name")]
            return sorted(names)
    except Exception:
        return []

def _build_options(context_size=None):
    """Shared Ollama options tuned for speed on CPU-only hardware."""
    return {
        "temperature": 0.0,
        "num_thread": _CPU_THREADS,
        "num_ctx": context_size if context_size else DEFAULT_CONTEXT_SIZE,
    }

_SIGNOFFS = ["have a great day", "have a nice day", "goodbye", "bye", "take care", "have fun", "see you", "thanks", "thank you"]
_SIGNOFF_FILLERS = ["", "so much", "a lot", "very much", "for your help", "for your patience"]
def _clean_answer(text):
    """Strip an ANSWER that is PURELY a conversational sign-off (e.g. the model's
    whole answer was just "Thanks!" or "Have a great day!").

    IMPORTANT: this must only match when the sign-off phrase IS the entire answer
    (plus a little trailing filler), not merely when the answer starts with one.
    A prefix check here would wipe out substantive answers like "Thanks for
    waiting, I found 3 matching files in ~/docs." just because they happen to
    open politely -- that's a real bug this guards against.
    """
    if not text:
        return text
    lower = text.strip().lower().rstrip(".!")
    for phrase in _SIGNOFFS:
        for filler in _SIGNOFF_FILLERS:
            candidate = (phrase + " " + filler).strip() if filler else phrase
            if lower == candidate:
                return ""
    return text

def search_duckduckgo(query):
    """Performs a live web search using the duckduckgo_search package."""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return "No web search results found."
            output = []
            for i, r in enumerate(results, 1):
                title = r.get('title', 'No Title')
                href = r.get('href', 'No URL')
                body = r.get('body', 'No Description')
                output.append(f"[{i}] {title}\n    URL: {href}\n    Summary: {body}")
            return "\n\n".join(output)
    except ImportError:
        return "Error: The 'duckduckgo_search' library is required for live web searches. Please install it using: pip install duckduckgo_search"
    except Exception as e:
        return f"Error during web search: {str(e)}"

def _store_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "litelaw_store.json")

def _load_store():
    try:
        with open(_store_path(), "r") as f:
            return json.load(f)
    except Exception:
        return {"chats": {}, "memories": [], "documents": {}, "reminders": {}}

def _save_store(data):
    with open(_store_path(), "w") as f:
        json.dump(data, f, indent=2)

def doc_list():
    store = _load_store()
    docs = store.get("documents", {})
    if not docs:
        return "No documents found."
    lines = []
    for did, doc in docs.items():
        lines.append(f"{did}: {doc.get('title', 'Untitled')}")
    return "\n".join(lines)

def doc_read(doc_id):
    store = _load_store()
    docs = store.get("documents", {})
    if doc_id in docs:
        return f"Title: {docs[doc_id]['title']}\nContent:\n{docs[doc_id]['content']}"
    for did, doc in docs.items():
        if doc.get("title", "").lower() == doc_id.lower():
            return f"Title: {doc['title']}\nContent:\n{doc['content']}"
    return f"Document '{doc_id}' not found."

def doc_write(doc_id, content):
    store = _load_store()
    docs = store.get("documents", {})
    if doc_id in docs:
        docs[doc_id]["content"] = content
        _save_store(store)
        return f"Document '{doc_id}' updated."
    for did, doc in docs.items():
        if doc.get("title", "").lower() == doc_id.lower():
            docs[did]["content"] = content
            _save_store(store)
            return f"Document '{doc_id}' updated."
    return f"Document '{doc_id}' not found."

def doc_new(title):
    import uuid
    store = _load_store()
    doc_id = uuid.uuid4().hex
    store.setdefault("documents", {})[doc_id] = {"title": title, "content": ""}
    _save_store(store)
    return f"Document '{title}' created (id: {doc_id})."

def doc_delete(doc_id):
    store = _load_store()
    docs = store.get("documents", {})
    if doc_id in docs:
        del docs[doc_id]
        _save_store(store)
        return f"Document '{doc_id}' deleted."
    for did, doc in list(docs.items()):
        if doc.get("title", "").lower() == doc_id.lower():
            del docs[did]
            _save_store(store)
            return f"Document '{doc_id}' deleted."
    return f"Document '{doc_id}' not found."

def doc_export(doc_id, filepath):
    store = _load_store()
    docs = store.get("documents", {})
    doc = docs.get(doc_id)
    if not doc:
        for did, d in docs.items():
            if d.get("title", "").lower() == doc_id.lower():
                doc = d
                break
    if not doc:
        return f"Document '{doc_id}' not found."
    try:
        with open(filepath, "w") as f:
            f.write(doc["content"])
        return f"Exported '{doc['title']}' to {filepath}"
    except Exception as e:
        return f"Export failed: {e}"

def doc_import(filepath):
    import uuid
    if not os.path.exists(filepath):
        return f"File not found: {filepath}"
    try:
        with open(filepath, "r") as f:
            content = f.read()
    except Exception as e:
        return f"Import failed: {e}"
    store = _load_store()
    doc_id = uuid.uuid4().hex
    title = os.path.basename(filepath)
    store.setdefault("documents", {})[doc_id] = {"title": title, "content": content}
    _save_store(store)
    return f"Imported '{title}' as document (id: {doc_id})."

def open_in_browser(url):
    """Opens a URL safely in the system's default web browser."""
    try:
        target_url = url.strip()
        if not (target_url.startswith("http://") or target_url.startswith("https://")):
            target_url = "https://" + target_url
        webbrowser.open(target_url)
        return f"Successfully opened URL in default browser: {target_url}"
    except Exception as e:
        return f"Error opening URL in browser: {str(e)}"

def get_system_prompt(memories=None):
    current_os = platform.system()
    
    memory_context = ""
    if memories:
        memory_context = "\n\nPERSISTENT CONTEXT & MEMORIES FROM PAST SESSIONS:\n" + "\n".join(f"- {m}" for m in memories)

    return f"""You are "litelaw", a computer automation agent. You run terminal commands to help users.{memory_context}

You have TWO actions:
1. RUN_COMMAND - run a terminal command
2. FINISHED - give final answer

FORMAT (you MUST use exactly this):
THOUGHT: what you're doing
ACTION: RUN_COMMAND
COMMAND: <the command>

Or when done:
THOUGHT: summary
ACTION: FINISHED
ANSWER: what you did

COMMANDS YOU CAN USE:
- mkdir -p ~/path/to/folder (create folder)
- touch ~/path/file.txt (create empty file)
- echo 'text content' > ~/path/file.txt (write text to file)
- rm ~/path/file.txt (delete file)
- rm -r ~/path/folder (delete folder)
- ls ~/path/ (list files)
- find ~/path -name "*.ext" (find files)
- python3 litelaw.py --search "query" (web search)
- python3 litelaw.py --open "url" (open in browser)

RULES:
- NEVER use python3 -c
- NEVER use --doc-write for files on disk (only for internal documents)
- Always use echo to write text to files
- Always use mkdir -p to create folders

CONVERSATIONAL MESSAGES (read this first, before anything else):
Not every message is a task. If the user is just greeting you, making small talk,
asking a general question, or saying thanks/bye — there is NOTHING to run a command
for. Skip RUN_COMMAND entirely and go straight to FINISHED with a normal reply.

Example:
  User: "hi"
  THOUGHT: This is just a greeting, no command needed.
  ACTION: FINISHED
  ANSWER: Hey! What can I help you with?

Example:
  User: "how are you"
  THOUGHT: Conversational message, no task to perform.
  ACTION: FINISHED
  ANSWER: Doing well, thanks for asking! What do you need?

NEVER use `echo` or any other command just to "say" something to the user. echo is
ONLY for writing text into a file on disk, never for talking to the user. Your
spoken reply always goes in ANSWER, never inside a COMMAND.

You operate in an execution loop:
1. Analyze the user's request.
2. Decide: is this a real task requiring a file/system operation, or just conversation?
3. Choose a step or action.
4. Output the action in the exact format required.

You have access to two actions:
1. RUN_COMMAND: Runs a shell command on the user's machine.
2. FINISHED: Provides the final natural language answer once the task is complete.

WORKFLOW - HOW TO USE THESE ACTIONS:
Step 1: You output RUN_COMMAND with a command.
Step 2: The system runs the command and sends you the output.
Step 3: You MUST then output FINISHED with your answer summarizing the results.
Example for a search query:
  Round 1: THOUGHT: I need to search for this.\nACTION: RUN_COMMAND\nCOMMAND: python3 litelaw.py --search "best laptop"
  Round 2 (after getting results): THOUGHT: I found the results, let me summarize.\nACTION: FINISHED\nANSWER: Based on my research, the best laptop is... (explain in natural language, don't dump raw data)

ABSOLUTELY FORBIDDEN COMMANDS:
- NEVER use `python3 -c` or `python -c`. It is ALWAYS WRONG. Your command will be REJECTED.
- NEVER use `python3 litlaw.py` or `python3 litalaw.py` or any typo. Always exactly `python3 litelaw.py`.
- NEVER invent flags or scripts that don't exist.
- ONLY use the exact commands listed in section 7 and 8 above.

CRITICAL FORMATTING INSTRUCTIONS:
You must ONLY respond in one of the two blocks below. Do not include extra conversational text outside these formats.

Format 1 (To execute a command):
THOUGHT: <your brief reasoning here>
ACTION: RUN_COMMAND
COMMAND: <the exact terminal command to run>

Format 2 (When the task is successfully done):
THOUGHT: <your final thought>
ACTION: FINISHED
ANSWER: <your final response to the user summarizing what you did>

CRITICAL - ANSWER rules (read carefully):
- Your ANSWER must NEVER contain the text the user asked you to write into a file.
- Your ANSWER must NEVER repeat the user's request back to them.
- Your ANSWER must ONLY summarize what you did (e.g. "Written to file.txt", "Created the directory").

Example of WRONG answer:
  User: "write have a great day to file.txt"
  ANSWER: "have a great day"
  This is WRONG — you echoed the file content as if it's your own message to the user.

Example of CORRECT answer:
  User: "write have a great day to file.txt"
  ANSWER: "Written 'have a great day' to file.txt."
  This is CORRECT — it summarizes the action.

Be efficient, concise, and accurate. Do not run infinite loops or destructive actions."""

def call_ollama(messages, model=None, context_size=None):
    resolved_model = model or MODEL
    if not resolved_model:
        print(f"\n\uf071  [Error] No model configured. Set the LITEMODEL environment variable, "
              f"or choose an installed model in Settings if you're using the web app.")
        return None
    payload = {
        "model": resolved_model,
        "messages": messages,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": _build_options(context_size)
    }
    req = urllib.request.Request(
        OLLAMA_URL, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            return res_json['message']['content']
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ""
        print(f"\n🛑 [Error] Ollama HTTP {e.code}: {error_body}")
        return None
    except urllib.error.URLError as e:
        print(f"\n🛑 [Error] Could not connect to Ollama. Ensure it's running. ({e.reason})")
        return None
    except Exception as e:
        print(f"\n🛑 [Error] Ollama response error: {e}")
        return None

def call_ollama_stream(messages, model=None, context_size=None):
    """Generator that yields tokens from Ollama as they arrive."""
    resolved_model = model or MODEL
    if not resolved_model:
        print(f"\n\uf071  [Error] No model configured. Set the LITEMODEL environment variable, "
              f"or choose an installed model in Settings if you're using the web app.")
        return
    payload = {
        "model": resolved_model,
        "messages": messages,
        "stream": True,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": _build_options(context_size)
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            for line in response:
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    if 'message' in chunk and 'content' in chunk['message']:
                        token = chunk['message']['content']
                        if token:
                            yield token
                    if chunk.get('done'):
                        break
                except json.JSONDecodeError:
                    continue
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else ""
        print(f"\n🛑 [Error] Ollama HTTP {e.code}: {error_body}")
        return
    except urllib.error.URLError as e:
        print(f"\n🛑 [Error] Could not connect to Ollama. Ensure it's running. ({e.reason})")
        return
    except Exception as e:
        print(f"\n🛑 [Error] Ollama response error: {e}")
        return

# Destructive command patterns that are ALWAYS blocked, regardless of AUTO_APPROVE.
# gemma3:1b can hallucinate dangerous commands confidently, so this guardrail is
# not optional -- AUTO_APPROVE bypassing the (y/n) prompt must never mean "no safety net".
_DESTRUCTIVE_PATTERNS = [
    r'rm\s+-rf\s+/(?!\S)',                    # rm -rf / (root wipe)
    r'rm\s+-rf\s+/\*',                         # rm -rf /*
    r'rm\s+-rf\s+~(?!\S)',                     # rm -rf ~ (home wipe)
    r'rm\s+-rf\s+\$HOME(?!\S)',
    r':\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:',  # classic fork bomb
    r'mkfs(\.\w+)?\s+/dev/',
    r'dd\s+.*of=/dev/(sd|nvme|hd|vd)',
    r'>\s*/dev/(sd|nvme|hd|vd)\w*',
    r'chmod\s+-R\s+000\s+/(?!\S)',
    r'chmod\s+-R\s+777\s+/(?!\S)',
    r'\b(shutdown|poweroff|halt|reboot)\b',
    r'wipefs\s+',
]

def _is_destructive_command(command):
    for pattern in _DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command):
            return True
    return False

# Binary names for common GUI apps -- checked against the first token of a
# command to decide whether it needs to be launched detached (see execute_command).
_GUI_APP_HINTS = [
    'code', 'codium', 'gimp', 'firefox', 'chromium', 'chromium-browser', 'google-chrome',
    'nautilus', 'thunar', 'pcmanfm', 'dolphin', 'gedit', 'kate', 'kwrite', 'libreoffice',
    'soffice', 'vlc', 'inkscape', 'blender', 'krita', 'xterm', 'gnome-terminal', 'konsole',
    'evince', 'okular', 'xdg-open', 'gvim', 'gnome-text-editor', 'eog', 'feh', 'mpv',
    'audacious', 'thunderbird', 'gnome-calculator', 'file-roller',
]

def execute_command(command):
    print(f"\n\uf071  [litelaw intends to run]: {command}")

    if _is_destructive_command(command):
        print("🛑 [Blocked] This command matches a destructive-action safety pattern and was NOT executed.")
        return ("REJECTED: This command was blocked by litelaw's safety guardrail because it looks "
                "destructive (e.g. wiping a disk, deleting the root/home directory, or a fork bomb). "
                "AUTO_APPROVE does not override this check. Choose a safer, more targeted command.")

    # Intercept custom web workspace hooks to maximize cross-platform speed and stability
    normalized_cmd = command.strip()
    # Fix any model typo of litelaw.py -> litelaw.py
    for typo in ['litlaw.py', 'litalaw.py', 'litalw.py', 'litalow.py', 'litelow.py', 'ltielaw.py', 'litelaw.py']:
        normalized_cmd = normalized_cmd.replace(typo, 'litelaw.py')

    # Intercept python3 -c patterns that use litelaw functions
    if re.search(r'python3?\s+-c', normalized_cmd):
        if 'search' in normalized_cmd.lower() or 'duckduckgo' in normalized_cmd.lower():
            return "REJECTED: python3 -c not allowed. Use: python3 litelaw.py --search \"query\""
        if 'open' in normalized_cmd.lower() or 'browser' in normalized_cmd.lower():
            return "REJECTED: python3 -c not allowed. Use: python3 litelaw.py --open \"url\""
        if 'doc' in normalized_cmd.lower():
            return "REJECTED: python3 -c not allowed. Use: python3 litelaw.py --doc-list, --doc-read, --doc-write, --doc-new, --doc-delete, --doc-export, --doc-import"
        return "REJECTED: python3 -c not allowed. NEVER use python3 -c. Use python3 litelaw.py --search, --open, or --doc-* commands."

    if "litelaw.py --search " in normalized_cmd:
        try:
            query = normalized_cmd.split("--search ", 1)[1].strip().strip('"').strip("'")
            return search_duckduckgo(query)
        except Exception as e:
            return f"Failed to parse search utility string: {str(e)}"
    elif "litelaw.py --open " in normalized_cmd:
        try:
            url = normalized_cmd.split("--open ", 1)[1].strip().strip('"').strip("'")
            return open_in_browser(url)
        except Exception as e:
            return f"Failed to parse target browser target URL: {str(e)}"
    elif "litelaw.py --doc-list" in normalized_cmd:
        return doc_list()
    elif "litelaw.py --doc-read " in normalized_cmd:
        try:
            doc_id = normalized_cmd.split("--doc-read ", 1)[1].strip().strip('"').strip("'")
            return doc_read(doc_id)
        except Exception as e:
            return f"Failed to parse doc-read: {e}"
    elif "litelaw.py --doc-write " in normalized_cmd:
        try:
            rest = normalized_cmd.split("--doc-write ", 1)[1].strip()
            if " " not in rest:
                return "Usage: --doc-write <id> <content>"
            doc_id = rest[:rest.index(" ")].strip().strip('"').strip("'")
            content = rest[rest.index(" ")+1:].strip().strip('"').strip("'")
            return doc_write(doc_id, content)
        except Exception as e:
            return f"Failed to parse doc-write: {e}"
    elif "litelaw.py --doc-new " in normalized_cmd:
        try:
            title = normalized_cmd.split("--doc-new ", 1)[1].strip().strip('"').strip("'")
            return doc_new(title)
        except Exception as e:
            return f"Failed to parse doc-new: {e}"
    elif "litelaw.py --doc-delete " in normalized_cmd:
        try:
            doc_id = normalized_cmd.split("--doc-delete ", 1)[1].strip().strip('"').strip("'")
            return doc_delete(doc_id)
        except Exception as e:
            return f"Failed to parse doc-delete: {e}"
    elif "litelaw.py --doc-export " in normalized_cmd:
        try:
            rest = normalized_cmd.split("--doc-export ", 1)[1].strip()
            if " " not in rest:
                return "Usage: --doc-export <id> <filepath>"
            doc_id = rest[:rest.index(" ")].strip().strip('"').strip("'")
            filepath = rest[rest.index(" ")+1:].strip().strip('"').strip("'")
            return doc_export(doc_id, filepath)
        except Exception as e:
            return f"Failed to parse doc-export: {e}"
    elif "litelaw.py --doc-import " in normalized_cmd:
        try:
            filepath = normalized_cmd.split("--doc-import ", 1)[1].strip().strip('"').strip("'")
            return doc_import(filepath)
        except Exception as e:
            return f"Failed to parse doc-import: {e}"
    
    if not AUTO_APPROVE:
        confirm = input("👉 Allow execution? (y/n): ").strip().lower()
        if confirm != 'y':
            return "Command aborted by user safety guardrails."
    else:
        print("⚡ [Auto-Approved Execution]")

    # GUI apps (editors, browsers, file managers, media players, etc.) never exit
    # on their own, so running them through subprocess.run(..., timeout=30) just
    # blocks for 30 seconds and then kills the app the user wanted opened. Launch
    # these detached instead: Popen + start_new_session=True so the app keeps
    # running independently of litelaw and the request returns immediately.
    first_token = os.path.basename(normalized_cmd.split()[0]) if normalized_cmd.split() else ""
    if first_token in _GUI_APP_HINTS:
        try:
            subprocess.Popen(
                command, shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                start_new_session=True
            )
            return f"Launched '{command}' (GUI app opened in the background)."
        except Exception as e:
            return f"Error launching GUI app: {str(e)}"

    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.returncode == 0 else result.stderr
        if not output.strip():
            return f"Command executed successfully with empty output (Exit code: {result.returncode})."
        return output
    except Exception as e:
        return f"Error executing command: {str(e)}"

def parse_response(response_text):
    if not response_text:
        return None, None
    # Normalize: split combined ACTION: RUN_COMMAND COMMAND: onto separate lines
    response_text = re.sub(r'(ACTION:\s*RUN_COMMAND)\s+(COMMAND:)', r'\1\n\2', response_text)
    response_text = re.sub(r'(ACTION:\s*FINISHED)\s+(ANSWER:)', r'\1\n\2', response_text)
    lines = response_text.strip().split('\n')
    action = None
    command_lines = []
    answer_lines = []
    
    is_command = False
    is_answer = False
    
    for line in lines:
        if line.startswith("MULTI_AGENT_LOG:") or line.strip().startswith("```"):
            continue
        if line.startswith("ACTION:"):
            act_val = line.replace("ACTION:", "").strip()
            if "RUN_COMMAND" in act_val:
                action = "RUN_COMMAND"
                is_command = True
                is_answer = False
            elif "FINISHED" in act_val:
                action = "FINISHED"
                is_answer = True
                is_command = False
        elif line.startswith("COMMAND:"):
            command_lines.append(line.replace("COMMAND:", "").strip())
            is_command = True
        elif line.startswith("ANSWER:"):
            answer_lines.append(line.replace("ANSWER:", "").strip())
            is_answer = True
        elif is_command and not line.startswith("THOUGHT:"):
            command_lines.append(line)
        elif is_answer and not line.startswith("THOUGHT:"):
            answer_lines.append(line)
            
    cmd_str = "\n".join(command_lines).strip()
    ans_str = "\n".join(answer_lines).strip()
    
    if not action:
        clean = response_text.strip()
        for prefix in ['THOUGHT:', 'ACTION:', 'COMMAND:', 'ANSWER:']:
            if clean.startswith(prefix):
                clean = clean[len(prefix):].strip()
        return "FINISHED", clean if clean else response_text.strip()

    return action, cmd_str if action == "RUN_COMMAND" else ans_str




def _is_write_request(text):
    """Check if a user request involves writing text content to a file."""
    triggers = ["write", "content", "text", "echo", "save", "print", "put", "add line"]
    lower = text.lower()
    return any(t in lower for t in triggers)

def run_agent(user_goal, session_messages):
    session_messages.append({"role": "user", "content": f"Task: {user_goal}"})
    
    max_steps = 10
    command_history = []
    for step in range(max_steps):
        print(f"🤖 [Step {step + 1}/{max_steps}] Thinking...", end="\r")
        response = call_ollama(session_messages)
        if response is None:
            break
            
        session_messages.append({"role": "assistant", "content": response})
        
        for line in response.split('\n'):
            if line.startswith("THOUGHT:"):
                print(f"💡 {line}")
                
        action, target = parse_response(response)
        
        if action == "RUN_COMMAND" and target:
            command_history.append(target)
            repeats = sum(1 for c in command_history[-3:] if c == target)
            if repeats >= 3:
                print(f"\n\uf071  [Loop Detected] Command '{target}' repeated {repeats} times. Forcing completion.\n")
                session_messages.append({
                    "role": "user",
                    "content": f"That command already ran successfully. The task is done. Say ACTION: FINISHED now."
                })
                continue
            elif repeats >= 2:
                print(f"\n\uf071  [Repetition Warning] Command '{target}' is repeating. Task may already be done.\n")
                cmd_output = execute_command(target)
                print(f"📊 [Output Captured]\n---")
                print(cmd_output.strip())
                print(f"---\n")
                session_messages.append({
                    "role": "user",
                    "content": f"Command output:\n{cmd_output}\n\nNote: You already ran this command. If it worked, say ACTION: FINISHED. Do NOT repeat the same command."
                })
                continue

            if target.strip().startswith("touch ") and _is_write_request(user_goal):
                print(f"\n\uf071  [Touch Misuse] You used 'touch' but the task requires writing content. "
                      f"Correcting: asking the model to use echo/printf instead.\n")
                session_messages.append({
                    "role": "user",
                    "content": "You used 'touch' which only creates empty files. This task requires writing content into the file. "
                               "Use printf or echo instead. For example: printf 'content here\\n' > filename"
                })
                continue

            cmd_output = execute_command(target)
            print(f"📊 [Output Captured]\n---")
            print(cmd_output.strip())
            print(f"---\n")
            session_messages.append({"role": "user", "content": f"Command output:\n{cmd_output}"})
        elif action == "FINISHED":
            cleaned = _clean_answer(target)
            print(f"\n🎯 [Task Finished]: {cleaned or target}\n")
            break
        else:
            session_messages.append({
                "role": "user", 
                "content": "Invalid layout. Return your move strictly using ACTION: RUN_COMMAND or ACTION: FINISHED."
            })
    else:
        print("\n🛑 Task stopped: Reached maximum safety limit steps.\n")
        
    if len(session_messages) > MAX_CONTEXT_MESSAGES:
        system_prompt = session_messages[0]
        session_messages[:] = [system_prompt] + session_messages[-(MAX_CONTEXT_MESSAGES - 1):]

if __name__ == "__main__":
    # Check for argument overrides to support nested command evaluation
    if len(sys.argv) > 1:
        if sys.argv[1] == "--search" and len(sys.argv) > 2:
            print(search_duckduckgo(sys.argv[2]))
            sys.exit(0)
        elif sys.argv[1] == "--open" and len(sys.argv) > 2:
            print(open_in_browser(sys.argv[2]))
            sys.exit(0)
        elif sys.argv[1] == "--doc-list":
            print(doc_list())
            sys.exit(0)
        elif sys.argv[1] == "--doc-read" and len(sys.argv) > 2:
            print(doc_read(sys.argv[2]))
            sys.exit(0)
        elif sys.argv[1] == "--doc-write" and len(sys.argv) > 3:
            print(doc_write(sys.argv[2], sys.argv[3]))
            sys.exit(0)
        elif sys.argv[1] == "--doc-new" and len(sys.argv) > 2:
            print(doc_new(sys.argv[2]))
            sys.exit(0)
        elif sys.argv[1] == "--doc-delete" and len(sys.argv) > 2:
            print(doc_delete(sys.argv[2]))
            sys.exit(0)
        elif sys.argv[1] == "--doc-export" and len(sys.argv) > 3:
            print(doc_export(sys.argv[2], sys.argv[3]))
            sys.exit(0)
        elif sys.argv[1] == "--doc-import" and len(sys.argv) > 2:
            print(doc_import(sys.argv[2]))
            sys.exit(0)

    print("====================================================")
    print(f" ⚡ Welcome to litelaw ({platform.system()} Environment) ⚡")
    print(" MODE: Hands-Free Auto-Approve Enabled 🚀 ")
    print("====================================================\n")

    if not MODEL:
        print(f"\uf071  No model configured. Set the LITEMODEL environment variable to an "
              f"installed Ollama model (e.g. `LITEMODEL=gemma3:1b python3 litelaw.py`) before "
              f"running a task.\n")

    # Load persistent memories from store for CLI sessions
    _cli_memories = None
    _cli_store_path = _store_path()
    if os.path.exists(_cli_store_path):
        try:
            with open(_cli_store_path, "r") as _f:
                _store_data = json.load(_f)
                _cli_memories = _store_data.get("memories")
        except Exception:
            pass
    
    session_messages = [{"role": "system", "content": get_system_prompt(_cli_memories)}]

    while True:
        try:
            user_input = input("litelaw ➔ ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting litelaw session. Goodbye!")
                break
            if user_input.lower() == 'clear':
                session_messages = [{"role": "system", "content": get_system_prompt()}]
                print("🧹 Memory cleared! Starting fresh context.")
                continue
            run_agent(user_input, session_messages)
            
        except KeyboardInterrupt:
            print("\n\nSession interrupted. Type 'exit' to leave cleanly.")
        except Exception as e:
            print(f"\nAn error occurred: {e}\n")
