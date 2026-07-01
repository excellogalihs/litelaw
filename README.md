![litelaw banner](banner1.jpeg)
# ⬡ litelaw

> A lightweight autonomous AI workspace for local computer automation powered by Ollama.

litelaw is a desktop AI agent that executes terminal tasks through a modern web interface. Instead of simply answering questions, litelaw plans actions, runs commands locally, observes the results, and continues until the requested task is complete.

Everything runs on your own machine using a local Ollama model.

---

# ✨ Features

## 🤖 Autonomous AI Agent

* Multi-step reasoning and execution loop
* Automatically executes terminal commands
* Observes command output before deciding the next step
* Stops automatically once the task is complete
* Built-in execution safety limits

---

## 💬 Chat Workspace

* Clean modern interface
* Multiple conversation threads
* Persistent chat history
* Automatic context management
* Live execution timeline
* Displays:

  * AI reasoning
  * Executed commands
  * Terminal output
  * Final responses

---

## 🧠 Persistent Memory

Teach litelaw permanent facts that survive restarts.

Examples:

* preferred coding style
* favorite terminal commands
* project conventions
* workflow preferences

These memories are automatically injected into every new conversation.

---

## 📝 Built-in Document Editor

A lightweight workspace for:

* Notes
* Drafts
* TODO lists
* Command snippets
* Scratch files

Features include:

* Multiple documents
* Save documents
* Create new documents
* Persistent storage

---

## 📅 Calendar & Reminders

Built directly into the workspace.

Features:

* Monthly calendar
* Daily reminders
* Reminder management
* Browser notifications
* Persistent reminder storage

---

## 🧮 Calculator

Quick calculator built into the sidebar.

Supports:

* Addition
* Subtraction
* Multiplication
* Division
* Decimal calculations
* Live expression preview

---

## 💾 Persistent Storage

Everything is stored locally.

Stored data includes:

* Chat history
* Long-term memories
* Documents
* Calendar reminders

No external database required.

---

## 🖥️ Cross Platform

Supports:

* Linux
* Windows
* macOS

Automatically generates platform-appropriate terminal commands.

---

## ⚡ Ollama Integration

Runs entirely on local models.

Current default model:

```
gemma3:1b
```

Changing models only requires editing one configuration variable.

---

# 🏗 Architecture

```
User
   │
   ▼
Flask Web UI
   │
   ▼
Autonomous Agent
   │
   ▼
Ollama
   │
   ▼
Reasoning
   │
   ▼
Terminal Commands
   │
   ▼
Command Output
   │
   ▼
AI decides next action
```

---

# 📁 Project Structure

```
.
├── app.py              # Flask web application
├── litelaw.py          # Autonomous AI agent
├── litelaw_store.json  # Persistent storage
└── README.md
```

---

# 🚀 Installation

## 1. Clone the repository

```bash
git clone https://github.com/yourusername/litelaw.git
cd litelaw
```

---

## 2. Install Python dependencies

```bash
pip install flask
```

---

## 3. Install Ollama

Install Ollama from:

https://ollama.com

---

## 4. Download a model

Example:

```bash
ollama pull gemma3:1b
```

---

## 5. Start Ollama

```bash
ollama serve
```

---

## 6. Launch litelaw

```bash
python app.py
```

Open:

```
http://localhost:5000
```

---

# 🛠 Example Tasks

```
Create a folder named Projects
```

```
Compress my Downloads folder
```

```
Show all running Python processes
```

```
Find every .iso file in Downloads
```

```
Create a README.md for this project
```

```
Rename every .txt file to lowercase
```

```
List disk usage
```

```
Show my git status
```

---

# 🧠 How It Works

Unlike a normal chatbot, litelaw follows an execution loop:

```
Think

↓

Generate command

↓

Execute command

↓

Read output

↓

Reason again

↓

Repeat

↓

Finish
```

This allows it to complete tasks requiring multiple terminal commands without additional user input.

---

# 🔒 Safety

Current safeguards include:

* Maximum execution step limit
* Structured command parsing
* Command timeout
* Optional execution confirmation mode
* Context trimming to prevent memory overflow

---

# ⚙ Configuration

Inside `litelaw.py` you can configure:

```python
MODEL = "gemma3:1b"
```

```python
AUTO_APPROVE = True
```

```python
MAX_CONTEXT_MESSAGES = 20
```

---

# 📦 Current Built-in Tools

* 🤖 Autonomous AI Agent
* 💬 Chat Workspace
* 🧠 Persistent Memory
* 📝 Document Editor
* 📅 Calendar
* 🔔 Reminders
* 🧮 Calculator
* 💾 Local Storage
* 🖥 Cross-platform terminal execution
* ⚡ Ollama integration

---

# 🗺 Planned Features

* Web search
* Deep research mode
* Local file indexing
* File search
* Webpage reader
* YouTube search
* Image understanding
* Voice input
* Plugin system
* Model selector
* Code editor
* File explorer
* Workspace tabs
* Multi-agent support

---

# 📜 License

This project is licensed under the MIT License.

---

# ⭐ Contributing

Contributions, ideas, bug reports, and feature requests are always welcome.

If you enjoy the project, consider giving it a ⭐ on GitHub.

You could also add badges (Python, Flask, Ollama, Linux/macOS/Windows, MIT, Stars, Last Commit, etc.) and a polished hero banner at the top to give it the look of larger open source projects like Open WebUI or Continue.
