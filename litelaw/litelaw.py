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
   - To CREATE files: On Linux/macOS use 'touch <file>'. On Windows use `type nul > <file>` (cmd) or `New-Item -ItemType File -Path <file>` (PowerShell).
   - To DELETE files: On Linux/macOS use 'rm <file>'. On Windows use `del <file>`.
   - To DELETE folders: On Linux/macOS use 'rm -r <dir>' (only use 'rm -rf' if the user explicitly confirms a forced/recursive delete is needed). On Windows use `rmdir /S /Q <dir>`.
   - To WRITE TEXT into a file: ALWAYS use a single-line command, never a multi-line heredoc. On Linux/macOS use `printf 'text\\n' > file`. On Windows use `echo text > file`.
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
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            return res_json['message']['content']
    except urllib.error.URLError as e:
        print(f"\n🛑 [Error] Could not connect to Ollama. Ensure it's running. ({e})")
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

# =====================================================================
# --- Multi-Agent Mode: Planner -> Researcher/Coder/Executor -> Reviewer
# =====================================================================
AGENT_ROLES = {
    "planner": "Planner",
    "researcher": "Researcher",
    "coder": "Coder",
    "executor": "Executor",
    "reviewer": "Reviewer",
}

def get_role_system_prompt(role, memories=None):
    """Builds a focused system prompt for a single specialist agent role."""
    current_os = platform.system()

    memory_context = ""
    if memories:
        memory_context = "\n\nPERSISTENT CONTEXT & MEMORIES FROM PAST SESSIONS:\n" + "\n".join(f"- {m}" for m in memories)

    base = f"""You are one specialist on "litelaw", a small local multi-agent automation team running on {current_os}.{memory_context}

You have access to two actions:
1. RUN_COMMAND: Runs a shell command on the user's machine.
2. FINISHED: Provides your final result for your assigned subtask once it's complete.

To search the live web, run: python3 litelaw.py --search "your search terms here"
To open a link in the browser, run: python3 litelaw.py --open "domain.com"

CRITICAL FORMATTING INSTRUCTIONS:
Respond ONLY in one of these two formats. No conversational text outside them.

Format 1 (to execute a command):
THOUGHT: <brief reasoning>
ACTION: RUN_COMMAND
COMMAND: <the exact terminal command to run>

Format 2 (when your subtask is done):
THOUGHT: <final thought>
ACTION: FINISHED
ANSWER: <your result for this subtask>
"""

    role_specific = {
        "researcher": """
ROLE: RESEARCHER
Gather the information needed for your assigned subtask (documentation, syntax, facts) using the search action above.
Stay focused, run at most a couple of searches, then FINISHED with a concise summary of what you found.
""",
        "coder": """
ROLE: CODER
Write or edit the files needed for your assigned subtask. Always use single-line file-writing commands
(e.g. `printf 'text\\n' > file` on Linux/macOS, or the Windows equivalent), never multi-line heredocs.
When the file(s) are written, respond FINISHED summarizing exactly what you created.
""",
        "executor": """
ROLE: EXECUTOR
Run and/or test the program or command for your assigned subtask. Confirm it behaves as expected,
then respond FINISHED describing the outcome (including any errors observed).
""",
        "reviewer": """
ROLE: REVIEWER
You do not run commands or use RUN_COMMAND. You only review the work the team already completed
against the original user request. Respond with ACTION: FINISHED. Your ANSWER MUST start with either
"PASS:" followed by a short summary for the user if the work looks complete and correct, or "FAIL:"
followed by what's missing or broken if it does not.
""",
    }
    return base + role_specific.get(role, "")


def run_planner(user_goal, memories=None):
    """Asks the Planner agent to break the goal into an ordered, agent-tagged checklist."""
    current_os = platform.system()
    memory_context = ""
    if memories:
        memory_context = "\n\nPERSISTENT CONTEXT & MEMORIES FROM PAST SESSIONS:\n" + "\n".join(f"- {m}" for m in memories)

    system_prompt = f"""You are the PLANNER on "litelaw", a small local multi-agent automation team running on {current_os}.{memory_context}

Break the user's request into a short ordered checklist of concrete, actionable subtasks (2 to 6 items).
Assign each subtask to exactly one teammate: "researcher" (gathering info/docs/web search), "coder" (writing or
editing files/code), or "executor" (running programs, commands, or tests). Do not include a "reviewer" step
yourself; a Reviewer is added automatically at the end.

Respond ONLY with a JSON array and nothing else (no markdown fences, no commentary), like:
[{{"agent": "researcher", "task": "Look up Flask quick-start docs"}}, {{"agent": "coder", "task": "Write app.py with a basic Flask route"}}, {{"agent": "executor", "task": "Run app.py and confirm it starts"}}]"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"User request: {user_goal}"},
    ]
    response = call_ollama(messages)
    if not response:
        return None

    text = response.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]

    try:
        start = text.index("[")
        end = text.rindex("]") + 1
        raw_tasks = json.loads(text[start:end])
        cleaned = []
        for t in raw_tasks:
            agent = str(t.get("agent", "executor")).lower().strip()
            if agent not in ("researcher", "coder", "executor"):
                agent = "executor"
            task_text = str(t.get("task", "")).strip()
            if task_text:
                cleaned.append({"agent": agent, "task": task_text})
        return cleaned if cleaned else None
    except Exception:
        return None


def run_task_step(role, task_text, memories=None, extra_context="", max_steps=4):
    """Runs a short, bounded ReAct loop for a single specialist agent on one subtask.
    Returns (steps, final_answer_text_or_None).
    """
    messages = [
        {"role": "system", "content": get_role_system_prompt(role, memories)},
        {"role": "user", "content": f"Your assigned subtask: {task_text}{extra_context}"},
    ]
    steps = []
    final_answer = None

    for _ in range(max_steps):
        response = call_ollama(messages)
        if not response:
            steps.append({"type": "error", "text": "Could not connect to Ollama. Ensure it's running.", "agent": role})
            break

        messages.append({"role": "assistant", "content": response})

        for line in response.split('\n'):
            if line.startswith("THOUGHT:"):
                steps.append({"type": "thought", "text": line.replace("THOUGHT:", "").strip(), "agent": role})

        action, target = parse_response(response)

        if action == "RUN_COMMAND" and target:
            steps.append({"type": "command", "text": target, "agent": role})
            output = execute_command(target)
            steps.append({"type": "output", "text": output.strip(), "agent": role})
            messages.append({"role": "user", "content": f"Command output:\n{output}"})
        elif action == "FINISHED":
            final_answer = target
            steps.append({"type": "final", "text": target, "agent": role})
            break
        else:
            messages.append({
                "role": "user",
                "content": "Invalid layout. Return your move strictly using ACTION: RUN_COMMAND or ACTION: FINISHED.",
            })

    return steps, final_answer


def run_reviewer(user_goal, completed_summary, memories=None):
    """Asks the Reviewer agent for a PASS/FAIL verdict on the team's completed work."""
    messages = [
        {"role": "system", "content": get_role_system_prompt("reviewer", memories)},
        {"role": "user", "content": f"Original user request: {user_goal}\n\nWork completed by the team:\n{completed_summary or '(nothing completed)'}"},
    ]
    response = call_ollama(messages)
    if not response:
        return "FAIL", "Could not connect to Ollama for review."

    action, target = parse_response(response)
    if action == "FINISHED" and target:
        verdict = "PASS" if target.upper().startswith("PASS") else "FAIL" if target.upper().startswith("FAIL") else "PASS"
        return verdict, target
    return "PASS", (response or "").strip()


def run_multi_agent(user_goal, memories=None):
    """Top-level orchestrator: Planner -> {Researcher, Coder, Executor} -> Reviewer.
    Returns a flat list of step dicts. 'task_queue' steps are periodic snapshots of the
    whole checklist (with per-item status) intended to drive a live progress UI.
    """
    steps = []

    plan = run_planner(user_goal, memories)
    if not plan:
        plan = [{"agent": "executor", "task": user_goal}]

    queue = [{"agent": t["agent"], "task": t["task"], "status": "pending"} for t in plan]
    steps.append({"type": "thought", "text": f"Plan created with {len(queue)} subtask(s).", "agent": "planner"})
    steps.append({"type": "task_queue", "queue": [dict(q) for q in queue], "agent": "planner"})

    completed_summaries = []
    accumulated_context = ""

    for i, item in enumerate(queue):
        queue[i]["status"] = "active"
        steps.append({"type": "task_queue", "queue": [dict(q) for q in queue], "agent": item["agent"]})

        role = item["agent"]
        task_steps, final_answer = run_task_step(role, item["task"], memories, extra_context=accumulated_context)
        steps.extend(task_steps)

        if final_answer:
            queue[i]["status"] = "done"
            completed_summaries.append(f"[{AGENT_ROLES.get(role, role)}] {item['task']} -> {final_answer}")
        else:
            queue[i]["status"] = "failed"
            completed_summaries.append(f"[{AGENT_ROLES.get(role, role)}] {item['task']} -> (did not finish cleanly)")

        accumulated_context = "\n\nContext from prior teammates:\n" + "\n".join(completed_summaries[-3:])
        steps.append({"type": "task_queue", "queue": [dict(q) for q in queue], "agent": role})

    queue.append({"agent": "reviewer", "task": "Review completed work against the original request", "status": "active"})
    steps.append({"type": "task_queue", "queue": [dict(q) for q in queue], "agent": "reviewer"})

    verdict, review_text = run_reviewer(user_goal, "\n".join(completed_summaries), memories)
    queue[-1]["status"] = "done" if verdict == "PASS" else "failed"
    steps.append({"type": "task_queue", "queue": [dict(q) for q in queue], "agent": "reviewer"})
    steps.append({"type": "review", "text": review_text, "verdict": verdict, "agent": "reviewer"})

    return steps


def run_agent(user_goal, session_messages):
    session_messages.append({"role": "user", "content": f"Task: {user_goal}"})
    
    max_steps = 10
    for step in range(max_steps):
        print(f"🤖 [Step {step + 1}/{max_steps}] Thinking...", end="\r")
        response = call_ollama(session_messages)
        if not response:
            break
            
        session_messages.append({"role": "assistant", "content": response})
        
        for line in response.split('\n'):
            if line.startswith("THOUGHT:"):
                print(f"💡 {line}")
                
        action, target = parse_response(response)
        
        if action == "RUN_COMMAND" and target:
            cmd_output = execute_command(target)
            print(f"📊 [Output Captured]\n---")
            print(cmd_output.strip())
            print(f"---\n")
            session_messages.append({"role": "user", "content": f"Command output:\n{cmd_output}"})
        elif action == "FINISHED":
            print(f"\n🎯 [Task Finished]: {target}\n")
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
        session_messages[:] = [system_prompt] + session_messages[-MAX_CONTEXT_MESSAGES:]

if __name__ == "__main__":
    # Check for argument overrides to support nested command evaluation
    if len(sys.argv) > 1:
        if sys.argv[1] == "--search" and len(sys.argv) > 2:
            print(search_duckduckgo(sys.argv[2]))
            sys.exit(0)
        elif sys.argv[1] == "--open" and len(sys.argv) > 2:
            print(open_in_browser(sys.argv[2]))
            sys.exit(0)

    print("====================================================")
    print(f" ⚡ Welcome to litelaw ({platform.system()} Environment) ⚡")
    print(" MODE: Hands-Free Auto-Approve Enabled 🚀 ")
    print(" TIP: prefix a goal with 'team ' or 'multi ' to run the")
    print("      Planner → Researcher/Coder/Executor → Reviewer crew")
    print("====================================================\n")
    
    session_messages = [{"role": "system", "content": get_system_prompt()}]

    def print_multi_agent_steps(steps):
        icons = {"pending": "□", "active": "◐", "done": "✓", "failed": "✕"}
        for step in steps:
            agent_tag = f"[{AGENT_ROLES.get(step.get('agent',''), step.get('agent','')).upper()}]" if step.get("agent") else ""
            if step["type"] == "task_queue":
                print("\n📋 [Task Queue]")
                for q in step["queue"]:
                    print(f"   {icons.get(q['status'], '□')} ({q['agent']}) {q['task']}")
                print()
            elif step["type"] == "thought":
                print(f"💡 {agent_tag} {step['text']}")
            elif step["type"] == "command":
                print(f"⚙️  {agent_tag} [running]: {step['text']}")
            elif step["type"] == "output":
                print(f"📊 {agent_tag} [output]\n---\n{step['text']}\n---")
            elif step["type"] == "review":
                mark = "✅" if step.get("verdict") == "PASS" else "⚠️"
                print(f"\n{mark} [REVIEWER] {step['text']}\n")
            elif step["type"] == "final":
                print(f"\n🎯 [Task Finished] {agent_tag} {step['text']}\n")
            elif step["type"] == "error":
                print(f"🛑 {agent_tag} {step['text']}")

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
            if user_input.lower().startswith('team ') or user_input.lower().startswith('multi '):
                goal = user_input.split(' ', 1)[1].strip()
                print("\n🤖 [Multi-Agent Mode] Planner → Researcher/Coder/Executor → Reviewer\n")
                steps = run_multi_agent(goal)
                print_multi_agent_steps(steps)
                continue

            run_agent(user_input, session_messages)
            
        except KeyboardInterrupt:
            print("\n\nSession interrupted. Type 'exit' to leave cleanly.")
        except Exception as e:
            print(f"\nAn error occurred: {e}\n")
