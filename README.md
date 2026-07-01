![litelaw banner](banner1.jpeg)
# ⬡ litelaw

> A lightweight autonomous AI workspace that combines a local LLM, terminal automation, persistent memory, document editing, and productivity tools into a single modern web interface.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python\&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20UI-000000?logo=flask)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-6E4AFF)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

**litelaw** is a local AI automation workspace designed to execute real computer tasks instead of simply chatting.

Using a locally running Ollama model, litelaw can reason through multi-step objectives, execute terminal commands, maintain persistent memories, organize conversations, edit documents, manage reminders, and provide a polished desktop-style workspace entirely on your own machine.

No cloud APIs are required.

---

# ✨ Features

## 🤖 Autonomous AI Agent

* Multi-step reasoning loop
* Automatic command execution
* Terminal output feedback
* Self-correcting execution pipeline
* Context-aware planning
* Configurable execution limit
* Auto-approve or manual approval modes

---

## 💻 Terminal Automation

Supports common developer workflows including:

* File management
* Folder management
* Process management
* Environment inspection
* Git operations
* Networking commands
* System diagnostics
* Archive management

The AI continually observes command output and decides the next action until the task is completed.

---

## 🧠 Persistent Long-Term Memory

Unlike normal chat sessions, litelaw includes persistent memory.

Features include:

* Save custom memories
* Delete memories
* Automatic injection into future conversations
* Preferences survive application restarts
* Shared across every chat thread

Example memories:

* preferred terminal style
* coding preferences
* recurring workflows
* project instructions

---

## 💬 Multi-Chat History

* Unlimited conversation threads
* Create new chats
* Persistent chat storage
* Restore previous conversations
* Automatic chat titles
* Context trimming to prevent token overflow

---

## 📝 Built-in Document Editor

A lightweight workspace editor included directly inside the UI.

Features:

* Create documents
* Edit documents
* Save documents
* Persistent storage
* Multiple document support
* Scratchpad workflow
* Quick note taking

---

## 📅 Calendar & Reminders

Integrated productivity tools include:

* Monthly calendar
* Reminder creation
* Reminder deletion
* Daily reminder notifications
* Browser notification support
* Persistent reminder storage

---

## 🧮 Calculator

Built directly into the workspace.

Features:

* Live evaluation
* Expression preview
* Standard arithmetic
* Backspace
* Clear
* Immediate results

---

## 🎨 Modern Workspace UI

The web interface includes:

* Animated starfield background
* Dark futuristic theme
* Sidebar navigation
* Chat history panel
* Document browser
* Auto-scroll chat
* Jump-to-latest button
* Responsive layout
* JetBrains Mono font
* Terminal-inspired design

---

## ⚡ Local First

Everything runs locally.

* No cloud APIs
* No subscriptions
* Fast response times
* Complete privacy
* Local execution
* Local storage

---

# 🏗 Architecture

```
User
 │
 ▼
Flask Web UI
 │
 ├── Chat Workspace
 ├── Memory Manager
 ├── Document Editor
 ├── Calculator
 ├── Calendar
 └── History Manager
 │
 ▼
litelaw Agent
 │
 ▼
Ollama
 │
 ▼
Local LLM
 │
 ▼
Terminal Execution
 │
 ▼
Operating System
```

---

# 📂 Project Structure

```
.
├── app.py
├── litelaw.py
├── litelaw_store.json
└── README.md
```

---

# 📦 Requirements

* Python 3.10+
* Flask
* Ollama
* Local Ollama model

Recommended model:

```
gemma3:1b
```

---

# 🚀 Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/litelaw.git

cd litelaw
```

Install Flask:

```bash
pip install flask
```

Install Ollama.

Pull the required model:

```bash
ollama pull gemma3:1b
```

Start Ollama:

```bash
ollama serve
```

Launch the workspace:

```bash
python app.py
```

Open:

```
http://localhost:5000
```

---

# 🖥 Using the Web Workspace

The web interface provides several built-in tools:

* Chat Workspace
* Long-Term Memory
* Document Editor
* Calculator
* Calendar
* Reminders
* Chat History

Simply describe a task, for example:

```
Create a folder called Projects.
```

```
Find every .iso file in Downloads.
```

```
Check git status.
```

```
Create notes.txt containing today's meeting notes.
```

The AI will:

1. Think
2. Generate a command
3. Execute it
4. Observe the output
5. Continue until finished

---

# 💾 Persistent Storage

litelaw stores data inside:

```
litelaw_store.json
```

Stored data includes:

* Chat history
* Memories
* Documents
* Calendar reminders

---

# ⚙ Configuration

Inside `litelaw.py` you can modify:

```python
MODEL = "gemma3:1b"
```

```python
AUTO_APPROVE = True
```

```python
MAX_CONTEXT_MESSAGES = 20
```

These allow you to change:

* AI model
* Safety confirmation
* Context window size

---

# 🔒 Safety

The execution loop includes several safeguards:

* Maximum execution steps
* Structured agent output parsing
* Context trimming
* Optional manual command approval
* Runtime error handling
* Invalid response recovery

---

# 🌟 Example Workflow

```
User:
Create a folder called Projects and move every .txt file into it.

↓

AI thinks

↓

Runs terminal command

↓

Reads terminal output

↓

Determines next step

↓

Runs another command

↓

Finishes automatically
```

---

# 🚧 Future Ideas

Potential future improvements include:

* Web search
* YouTube search
* File indexing
* Local RAG
* Vision support
* Voice interaction
* Plugin system
* Multi-model support
* Code editor
* File explorer
* Task scheduling
* Workflow automation
* MCP integration
* Agent tool ecosystem

---

# 📜 License

This project is released under the MIT License.

---

# Acknowledgements

* Ollama
* Flask
* JetBrains Mono
* Python

---

## ⭐ Why litelaw?

Unlike traditional chatbots, **litelaw** is designed to **act**, not just respond.

It combines an autonomous execution loop, persistent memory, productivity tools, and a polished local-first workspace into a lightweight AI assistant that lives entirely on your own computer.
