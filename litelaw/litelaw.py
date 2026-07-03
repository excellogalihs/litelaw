#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import urllib.request
import urllib.error
import platform
import webbrowser

# --- Configuration ---
MODEL = "gemma3:1b"
OLLAMA_URL = "http://localhost:11434/api/chat"
AUTO_APPROVE = True  # Set to True to bypass the (y/n) confirmation prompt
MAX_CONTEXT_MESSAGES = 20  # Safeguard to prevent context window bloat

_SIGNOFFS = ["have a great day", "have a nice day", "goodbye", "bye", "take care", "have fun", "see you", "thanks", "thank you"]
def _clean_answer(text):
    if not text:
        return text
    lower = text.strip().lower()
    for phrase in _SIGNOFFS:
        if lower == phrase or lower.startswith(phrase + " ") or lower.startswith(phrase + ".") or lower.startswith(phrase + "!"):
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

    return f"""You are "litelaw", a lightweight, elite computer automation agent running locally. 
Your job is to help the user complete daily computer tasks using the terminal.{memory_context}

The user's current Operating System environment is: {current_os}

You excel at these daily developer and desktop workflows. Generate exact syntax for {current_os}:
1. Application Lifecycle:
   - To CLOSE/QUIT apps: On Linux/macOS, use 'pkill <name>' or 'killall <name>'. On Windows, use 'taskkill /IM <name>.exe /F'. NEVER invent flags like '-quit'.
2. File & Archive Management (mkdir, echo, touch, cp, mv, rm, ls, find, grep, tar, zip, unzip):
   - CRITICAL: When asked to find or list specific file types (like .iso, .mp4, .txt files), do NOT just list the entire directory with a generic 'ls -l'. 
    - Instead, use precise filters. On macOS/Linux, use wildcards like `ls ~/Downloads/*.iso` or `find ~/Downloads -name "*.iso"`. On Windows, use `dir %USERPROFILE%\\Downloads\\*.iso`.
    - CRITICAL: When the user asks to write TEXT/CONTENT into a file (e.g. "write 'hello' to file.txt"), you MUST use `printf` or `echo`. NEVER use `touch` — touch only creates empty files and CANNOT write content.
    - To WRITE TEXT into a file: ALWAYS use a single-line command, never a multi-line heredoc. On Linux/macOS use `printf 'text\\n' > file` or `echo 'text' > file`. On Windows use `echo text > file`.
    - CRITICAL: When the user gives you text to write into a file, that text is file CONTENT, not a message for you. Do NOT echo it back in your ANSWER. Your ANSWER should only say what you did (e.g. "Written to file.txt").
    - To CREATE an empty file (no content): use `touch <file>` on Linux/macOS. On Windows use `type nul > <file>` (cmd) or `New-Item -ItemType File -Path <file>` (PowerShell).
    - To DELETE files: On Linux/macOS use 'rm <file>'. On Windows use `del <file>`.
    - To DELETE folders: On Linux/macOS use 'rm -r <dir>' (only use 'rm -rf' if the user explicitly confirms a forced/recursive delete is needed). On Windows use `rmdir /S /Q <dir>`.
3. System Diagnostics & Health (ps, top, df, free, uptime, lsof, env)
4. Git Version Control (git status, git diff, git add, git commit, git log, git branch)
5. Environment Diagnostics (python --version, pip list, node -v, npm list, docker ps)
6. Networking & Web (curl, wget, ping, nslookup)
7. Live Web Search & Browser Integration (Crucial Superpowers):
   - To SEARCH the live web for real-time definitions, information, or context, run:
     python3 litelaw.py --search "your search terms here"
   - To OPEN a specific link or domain in the user's default browser, run:
     python3 litelaw.py --open "domain.com"
   - To search within a specific platform via the browser (e.g., opening YouTube to search for "mrbeast"), construct the native platform search query URL and launch it. 
     Example: python3 litelaw.py --open "https://www.youtube.com/results?search_query=mrbeast"
    - Always prioritize these automated internal commands over raw `curl` or third-party web tools.
 8. Document Editor (Built-in Workspace Buffers):
    - litelaw has a built-in document editor that stores text documents persistently.
    - Use these commands to CREATE, READ, UPDATE, and DELETE documents at any time.
    - When documents are attached as pinned context above your instructions, you can freely edit them using their document ID.
    - To LIST all documents: python3 litelaw.py --doc-list
    - To READ a document: python3 litelaw.py --doc-read "document-id-or-title"
    - To WRITE/UPDATE content to a document: python3 litelaw.py --doc-write "doc-id" "full content here"
    - To CREATE a new document: python3 litelaw.py --doc-new "filename.txt"
    - To DELETE a document: python3 litelaw.py --doc-delete "doc-id-or-title"
    - To EXPORT a document to a file: python3 litelaw.py --doc-export "doc-id" "/path/to/file.txt"
    - To IMPORT a file as a document: python3 litelaw.py --doc-import "/path/to/file.txt"
    - IMPORTANT: When the user asks you to edit/create/delete a document, use these commands. 
      Do NOT use shell file operations (echo/printf/rm) for document editor operations.

You operate in an execution loop:
1. Analyze the user's request.
2. Choose a step or action.
3. Output the action in the exact format required.

You have access to two actions:
1. RUN_COMMAND: Runs a shell command on the user's machine.
2. FINISHED: Provides the final natural language answer once the task is complete.

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

def call_ollama(messages):
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }
    req = urllib.request.Request(
        OLLAMA_URL, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
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

def execute_command(command):
    print(f"\n⚙️  [litelaw intends to run]: {command}")
    
    # Intercept custom web workspace hooks to maximize cross-platform speed and stability
    normalized_cmd = command.strip()
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
            elif "FINISHED" in act_val:
                action = "FINISHED"
                is_answer = True
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
                print(f"\n⚠️  [Loop Detected] Command '{target}' repeated {repeats} times. Forcing completion.\n")
                session_messages.append({
                    "role": "user",
                    "content": f"That command already ran successfully. The task is done. Say ACTION: FINISHED now."
                })
                continue
            elif repeats >= 2:
                print(f"\n⚠️  [Repetition Warning] Command '{target}' is repeating. Task may already be done.\n")
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
                print(f"\n⚠️  [Touch Misuse] You used 'touch' but the task requires writing content. "
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

    # Load persistent memories from store for CLI sessions
    _cli_memories = None
    _store_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "litelaw_store.json")
    if os.path.exists(_store_path):
        try:
            with open(_store_path, "r") as _f:
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
