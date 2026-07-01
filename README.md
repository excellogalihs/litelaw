![litelaw banner](banner1.jpeg)
# ⚡ litelaw

> A lightweight autonomous AI workspace for local computer automation, persistent memory, document editing, file conversion, and intelligent terminal control powered by Ollama.

---

## ✨ Overview

**litelaw** is a local AI workspace that combines an autonomous terminal agent with a modern desktop-inspired web interface.

Instead of acting as a simple chatbot, litelaw can:

* execute terminal commands
* remember information across sessions
* manage multiple chat threads
* edit documents
* convert files
* manage reminders
* perform live web searches
* launch websites
* work entirely with locally hosted AI models through **Ollama**

Everything runs locally, giving you full control over your data and workflow.

---

# Features

## 🤖 Autonomous AI Agent

* Local AI powered by Ollama
* Multi-step reasoning loop
* Automatic terminal command execution
* Command output feedback
* Context-aware conversations
* Auto-approved execution mode (configurable)
* Cross-platform system prompts
* Linux, macOS, and Windows support

---

## 💬 Chat Workspace

* Multiple chat sessions
* Chat history sidebar
* Create new conversations
* Automatic conversation titles
* Persistent conversation storage
* Context trimming to prevent token overflow

---

## 🧠 Persistent Memory

Long-term memory survives application restarts.

Examples include:

* user preferences
* workflow rules
* coding styles
* frequently used instructions

Memories are automatically injected into the AI system prompt for every conversation.

---

## 📝 Document Editor

Built-in lightweight editor featuring:

* create documents
* save documents
* load documents
* rename documents
* persistent storage
* sidebar document browser

Perfect for:

* notes
* prompts
* scratchpads
* code snippets
* task lists

---

## 🔄 File Converter

Supports multiple document and image conversions.

### Supported conversions

| From | To   |
| ---- | ---- |
| PDF  | TXT  |
| PDF  | DOCX |
| DOCX | PDF  |
| DOCX | TXT  |
| PNG  | JPEG |
| JPEG | PNG  |
| PNG  | PDF  |
| JPEG | PDF  |

Includes:

* drag & drop interface
* browser downloads
* no external services required

---

## 📅 Calendar & Reminders

* monthly calendar
* add reminders
* delete reminders
* persistent reminder storage
* reminder indicators

---

## 🧮 Calculator

Built-in calculator featuring:

* basic arithmetic
* keyboard-friendly interface
* lightweight operation
* no external libraries

---

## 🌐 Web Utilities

The agent can:

* search the web
* open websites
* launch platform-specific searches
* use browser integration

Examples:

* Google searches
* YouTube searches
* documentation lookup
* opening URLs directly

---

## 🎨 Modern Interface

Features include:

* desktop-style layout
* dark futuristic theme
* animated starfield background
* responsive design
* JetBrains Mono typography
* custom sidebar
* smooth scrolling
* terminal-inspired command blocks

---

## 💾 Persistent Storage

All workspace data is stored locally.

Stored data includes:

* chat history
* memories
* documents
* reminders

No cloud database required.

---

# Project Structure

```text
.
├── app.py                 # Flask web application
├── litelaw.py             # AI engine & terminal agent
├── litelaw_store.json     # Persistent storage
└── README.md
```

---

# Requirements

* Python 3.10+
* Ollama
* A downloaded Ollama model (default: `gemma3:1b`)

Python packages:

```bash
pip install flask pillow python-docx pypdf
```

For web search support:

```bash
pip install ddgs
```

---

# Installing

Clone the repository:

```bash
git clone https://github.com/yourusername/litelaw.git
```

Enter the project:

```bash
cd litelaw
```

Install dependencies:

```bash
pip install flask pillow python-docx pypdf ddgs
```

Install Ollama:

```bash
ollama pull gemma3:1b
```

Start Ollama:

```bash
ollama serve
```

Launch the web interface:

```bash
python app.py
```

---

# Usage

Open your browser and visit:

```text
http://127.0.0.1:5000
```

You can then:

* create AI conversations
* manage memories
* edit documents
* convert files
* use the calculator
* manage reminders
* automate terminal tasks

---

# Example Prompts

```text
Create a folder called Projects
```

```text
Find every .pdf file in Downloads
```

```text
Search the web for Python async tutorials
```

```text
Open YouTube and search for Arch Linux
```

```text
Check my disk usage
```

```text
Show running Python processes
```

---

# Configuration

Inside `litelaw.py` you can customize:

```python
MODEL = "gemma3:1b"

AUTO_APPROVE = True

MAX_CONTEXT_MESSAGES = 20
```

---

# Technologies Used

* Python
* Flask
* Ollama
* HTML
* CSS
* JavaScript
* Pillow
* python-docx
* pypdf
* DDGS

---

# Roadmap

Planned improvements include:

* Browser automation
* Voice input
* Vision support
* Plugin system
* Better file indexing
* Local RAG
* Workspace search
* Native markdown preview
* Code editor
* Multiple AI providers
* Workflow automation
* Deep research mode

---

# Contributing

Contributions are welcome.

Feel free to open issues, suggest improvements, or submit pull requests.

---

# License

This project is licensed under the MIT License.

---

## ⭐ If you enjoy this project...

Give the repository a ⭐ to support future development!
