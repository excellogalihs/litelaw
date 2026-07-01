#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import urllib.request
import urllib.error
import platform

# --- Configuration ---
MODEL = "gemma3:1b"
OLLAMA_URL = "http://localhost:11434/api/chat"
AUTO_APPROVE = True  # Set to True to bypass the (y/n) confirmation prompt
MAX_CONTEXT_MESSAGES = 20  # Safeguard to prevent context window bloat

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
   - To OPEN/LAUNCH apps: On macOS use 'open -a', Linux use 'xdg-open', Windows use 'start'.
2. File & Archive Management (mkdir, echo, touch, cp, mv, rm, ls, find, grep, tar, zip, unzip):
   - CRITICAL: When asked to find or list specific file types (like .iso, .mp4, .txt files), do NOT just list the entire directory with a generic 'ls -l'. 
   - Instead, use precise filters. On macOS/Linux, use wildcards like `ls ~/Downloads/*.iso` or `find ~/Downloads -name "*.iso"`. On Windows, use `dir %USERPROFILE%\\Downloads\\*.iso`.
   - To CREATE folders: On Linux/macOS use 'mkdir -p <path>'. On Windows use 'mkdir <path>' (cmd) or `New-Item -ItemType Directory -Path <path>` (PowerShell).
   - To CREATE files: On Linux/macOS use 'touch <file>'. On Windows use `type nul > <file>` (cmd) or `New-Item -ItemType File -Path <file>` (PowerShell).
   - To DELETE files: On Linux/macOS use 'rm <file>'. On Windows use `del <file>`.
   - To DELETE folders: On Linux/macOS use 'rm -r <dir>' (only use 'rm -rf' if the user explicitly confirms a forced/recursive delete is needed). On Windows use `rmdir /S /Q <dir>`.
   - To WRITE TEXT into a file: ALWAYS use a single-line command, never a multi-line heredoc (heredocs span multiple lines and are unreliable to generate correctly). On Linux/macOS use `printf 'text\n' > file` to overwrite or `printf 'text\n' >> file` to append. For multiple lines in one shot, put literal `\n` inside the printf string, e.g. `printf 'line one\nline two\nline three\n' > file`. Plain `echo "text" > file` also works for simple single-line writes. On Windows use `echo text > file` (cmd) to overwrite or `echo text >> file` to append, or `Set-Content -Path file -Value "text"` / `Add-Content -Path file -Value "text"` (PowerShell) for multi-line content, joining lines with `` `n ``.
3. System Diagnostics & Health (ps, top, df, free, uptime, lsof, env)
4. Git Version Control (git status, git diff, git add, git commit, git log, git branch)
5. Environment Diagnostics (python --version, pip list, node -v, npm list, docker ps)
6. Networking & Web (curl, wget, ping, nslookup)

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
    print("====================================================")
    print(f" ⚡ Welcome to litelaw ({platform.system()} Environment) ⚡")
    print(" MODE: Hands-Free Auto-Approve Enabled 🚀 ")
    print("====================================================\n")
    
    session_messages = [{"role": "system", "content": get_system_prompt()}]
    
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
