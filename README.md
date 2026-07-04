![litelaw banner](banner.jpeg)
# ⬡ litelaw

> A lightweight local AI workspace powered by Ollama.
>
> Run autonomous AI tasks, execute terminal commands, manage documents, search the web, remember information across sessions, and interact through a modern desktop-style interface.

---

## Features

### 🤖 Autonomous AI Agent

- Powered by local Ollama models
- Multi-step reasoning loop
- Executes terminal commands automatically
- Streaming responses with live thoughts
- Loop detection and recovery
- Command safety checks
- Configurable context window

---

### 💬 AI Chat Workspace

- Persistent chat history
- Multiple conversations
- Live token streaming
- Automatic conversation titles
- Session memory
- Modern desktop UI

---

### 🧠 Persistent Memory

Store information that survives between sessions.

Examples:

- Personal preferences
- Coding conventions
- Frequently used instructions
- Project context

The AI automatically receives these memories inside its system prompt.

---

### 📄 Document Workspace

Built-in document editor with AI editing.

Features include:

- Create documents
- Edit with AI
- Save locally
- Import text files
- Export documents
- Multiple document workspaces

The AI can:

- Rewrite
- Expand
- Summarize
- Fix grammar
- Generate content

---

### 🌐 Web Search

Built-in DuckDuckGo search.

The AI can:

- Search the web
- Read search summaries
- Use results during reasoning
- Open URLs in your browser

---

### 🖥 Terminal Automation

The AI can execute commands such as:

- Create folders
- Create files
- Write text
- Delete files
- Find files
- List directories
- Open websites

Safety mechanisms include:

- Infinite loop detection
- Invalid command rejection
- Command formatting validation
- Automatic completion detection

---

### 📅 Calendar Reminders

- Create reminders
- Delete reminders
- Persistent storage
- Calendar integration

---

### 📁 File Conversion

Supports conversions including:

| From | To |
|-------|----|
| PDF | TXT |
| PDF | DOCX |
| DOCX | TXT |
| PNG | JPEG |
| JPEG | PNG |
| PNG | PDF |
| JPEG | PDF |

---

### ⚙ Settings

Configure:

- Ollama model
- Context size

The selected configuration is saved automatically.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/excellogalihs/litelaw.git
cd litelaw
```

---

### 2. Install Python

Python 3.10 or newer is recommended.

---

### 3. Install Ollama

Download:

https://ollama.com

Start Ollama:

```bash
ollama serve
```

Pull a model:

```bash
ollama pull gemma3:1b
```

or any other supported model.

---

### 4. Install dependencies

```bash
pip install flask pillow python-docx pypdf duckduckgo_search
```

---

### 5. Start litelaw

```bash
python app.py
```

Open:

```
http://localhost:5000
```

---

## Requirements

- Python 3.10+
- Ollama
- Local LLM (Gemma 3, Llama, Qwen, etc.)

Python packages:

```
Flask
Pillow
python-docx
pypdf
duckduckgo_search
```

---

## Supported Models

Any Ollama chat model should work, including:

- gemma3:1b
- gemma3:4b
- llama3.2:1b
- llama3.2:3b

---

## Project Structure

```
litelaw/
│
├── app.py
├── litelaw.py
├── litelaw_store.json
├── README.md
└── ...
```

---

## Storage

litelaw stores data locally.

Persistent data includes:

- Chats
- Memories
- Documents
- Reminders
- Settings

No cloud services are required.

---

## Built With

- Python
- Flask
- Ollama
- DuckDuckGo Search
- Pillow
- python-docx
- pypdf

---

## Roadmap

Planned improvements:

- Multi-agent workflows
- Better persistent memory
- File indexing
- Semantic search
- RAG support
- Plugin system
- Voice interaction
- Image understanding
- Better autonomous planning
- Local vector database

---

## License

MIT License

---

## Acknowledgements

- Ollama
- Google Gemma
- DuckDuckGo Search
- Flask

---

# ⬡ litelaw

A lightweight local AI workspace designed for autonomous computer assistance while remaining fast enough to run on small local language models.
