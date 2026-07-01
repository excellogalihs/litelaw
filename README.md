![litelaw banner](banner1.jpeg)
# ⬡ litelaw

> A lightweight autonomous AI workspace for local computer automation powered by Ollama.

litelaw is a local-first AI automation environment that combines an autonomous terminal agent with a modern web interface. It can reason through tasks, execute terminal commands, maintain persistent memory across sessions, manage multiple chat threads, and provide a built-in document editor.

Everything runs locally.

---

# Features

## 🤖 Autonomous Terminal Agent

- Multi-step reasoning loop
- Executes terminal commands automatically
- Reads command output and continues reasoning
- Stops once the task is complete
- Configurable execution safety

---

## 💬 Chat History

- Multiple conversation threads
- Persistent conversations
- Automatic context management
- Reload previous sessions

---

## 🧠 Persistent Memory

Long-term memory survives restarts.

Perfect for storing things like:

- preferred coding style
- favorite commands
- project rules
- personal preferences
- workflow instructions

Every new chat automatically receives your saved memories.

---

## 📝 Built-in Document Editor

Includes a lightweight document workspace.

Features:

- Create documents
- Edit documents
- Save documents
- Persistent storage
- Scratchpad for notes, prompts, templates, etc.

---

## 🎨 Modern UI

- Dark futuristic theme
- Animated starfield background
- Responsive interface
- Sidebar workspace
- Chat bubbles
- Terminal-style command output
- Separate workspaces for:

  - Chat
  - Memory
  - Documents

---

## ⚡ Local Execution

Runs commands directly on your machine.

Supports operating-system-aware command generation for:

- Linux
- Windows
- macOS

The AI automatically adapts command syntax depending on the OS.

---

## 🔄 Autonomous Execution Loop

The agent repeatedly performs:

1. Think
2. Generate command
3. Execute command
4. Read output
5. Decide next action
6. Repeat until finished

---

## 📦 Persistent Workspace

Workspace state is stored inside

```
litelaw_store.json
```

This includes:

- chat history
- memories
- saved documents

---

# Project Structure

```
litelaw/
│
├── app.py                 # Flask web application
├── litelaw.py             # AI agent engine
├── litelaw_store.json     # Persistent workspace storage
├── README.md
```

---

# Requirements

## Python

Python 3.10+

---

## Ollama

Install Ollama:

https://ollama.com

Start the server:

```bash
ollama serve
```

---

## AI Model

Current default:

```
gemma3:1b
```

Pull it using:

```bash
ollama pull gemma3:1b
```

You can change the model inside:

```python
MODEL = "gemma3:1b"
```

---

## Python Packages

Install Flask:

```bash
pip install flask
```

The remaining modules are part of Python's standard library.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/excellogalihs/litelaw.git
```

Enter the directory:

```bash
cd litelaw
```

Install dependencies:

```bash
pip install flask
```

Start Ollama:

```bash
ollama serve
```

Run the web interface:

```bash
python app.py
```

Open your browser:

```
http://localhost:5000
```

---

# Usage

Type natural language requests such as:

```
Create a folder called Projects
```

```
Find all ISO files in Downloads
```

```
Show Python version
```

```
List running Docker containers
```

```
Create a README file
```

The agent will:

- think
- execute commands
- inspect results
- continue automatically
- return a final response

---

# Supported Tasks

## File Management

- create files
- delete files
- move files
- rename files
- search directories
- archives
- copy files

---

## Development

- Git
- Python
- Node.js
- Docker
- Pip
- NPM

---

## System Diagnostics

- processes
- memory
- disk usage
- environment variables
- uptime
- networking

---

## Terminal Automation

- shell commands
- automation workflows
- command execution
- multi-step tasks

---

# Persistent Memory

Memories can be added through the web interface.

Example memories:

```
Always use printf instead of echo.
```

```
Prefer Python over Bash when possible.
```

```
Use Arch Linux package manager.
```

Every future conversation automatically includes these memories.

---

# Document Workspace

Built-in editor supports:

- notes
- prompt libraries
- command templates
- scratchpads
- temporary files

Documents remain available after restarting the application.

---

# Safety

The agent currently supports automatic execution.

Configuration:

```python
AUTO_APPROVE = True
```

Set it to:

```python
AUTO_APPROVE = False
```

to require confirmation before every command.

---

# Configuration

Inside `litelaw.py`

```python
MODEL = "gemma3:1b"
```

Change to any installed Ollama model.

Example:

```
llama3
```

```
qwen3
```

```
phi4
```

```
deepseek-r1
```

You can also configure:

- maximum context size
- Ollama endpoint
- auto-approval
- timeout behavior

---

# Future Roadmap

Planned features include:

- Web search
- Webpage reader
- YouTube search
- Local file indexing
- Semantic document search
- Vision support
- Voice support
- Plugin system
- Multi-agent workflows
- Deep research mode
- Code editor
- File explorer
- Model manager
- Better permission controls
- Streaming responses
- Markdown rendering
- Syntax highlighting
- Download manager
- Background task execution
- Workspace tabs
- Custom themes

---

# License

This project is provided as-is for educational and personal use.

---

# Acknowledgements

- Ollama
- Flask
- JetBrains Mono
- Python

---

## Built for local AI automation.

**Think. Execute. Learn. Repeat.**
