![litelaw banner](banner.jpeg)
# ⬡ litelaw

**litelaw** is a self-hosted, zero-API-key AI agent dashboard that runs entirely on your own machine using local models via [Ollama](https://ollama.com). It combines a ReAct-style terminal automation agent, a multi-agent planner/executor/reviewer pipeline, a document workspace, a calendar, a file converter, and persistent memory — all wrapped in a custom dark violet "outer space" themed Flask web UI.

No cloud calls, no API keys, no telemetry. Everything runs locally against your own Ollama instance.

![Python](https://img.shields.io/badge/python-3.9+-blue)
![Flask](https://img.shields.io/badge/flask-web%20UI-black)
![Ollama](https://img.shields.io/badge/ollama-local%20inference-purple)

---

## ✨ Features

### 🤖 Local AI Agent
- **ReAct-style execution loop** — the model reasons in `THOUGHT`, then acts via `RUN_COMMAND` or finishes with `FINISHED` / `ANSWER`, looping until the task is complete or a safety limit is hit.
- **Multi-agent mode** — an optional Planner → Executor → Reviewer flow that breaks a goal into subtasks, executes them, and has a reviewer verify and produce the final answer.
- **Streaming responses** via Server-Sent Events for real-time token-by-token output, thoughts, commands, and command output in the UI.
- **Loop & misuse detection** — automatically detects repeated commands, forces task completion after too many steps, and corrects common model mistakes (e.g. using `touch` when the task requires writing file content).
- **Safety guardrails** — a hardcoded blocklist rejects destructive commands (`rm -rf /`, fork bombs, disk wipes, `mkfs`, `shutdown`, etc.) regardless of auto-approve settings.
- **Web search** built in (DuckDuckGo via the `ddgs` package) so the agent can look things up without any API key.
- **Browser control** — the agent can open URLs directly in your system's default browser.

### 🧠 Persistent Memory
- SQLite/JSON-backed memory store that persists facts and preferences across sessions, inspired by the Odysseus memory architecture.
- Add, view, and delete individual memories, which are automatically injected into the agent's system prompt.

### 📄 Document Workspace
- Create, edit, save, rename, and delete lightweight text documents inside the app.
- Import existing text files into the workspace, or export a document straight back to disk.
- A default scratchpad document is created out of the box for notes, task definitions, or command templates.

### 🔁 File Conversion
- Built-in converter supporting PDF ⇄ TXT, DOCX ⇄ TXT, PDF → DOCX, and more, powered by `pypdf` and `python-docx`.

### 📅 Calendar & Reminders
- Full interactive calendar with per-date reminders.
- Native desktop notifications and an in-app banner for reminders due today.

### 🎛️ Chat & Settings
- Multiple persistent chat threads with titles, stored locally in a JSON store.
- Live model picker pulled straight from your installed Ollama models (`ollama list`).
- Adjustable context window size (`num_ctx`) per session to balance speed vs. context on weaker hardware.

### 🎨 UI
- Fully custom dark violet / "outer space" theme, no default Bootstrap look.
- Nerd Font glyph icons throughout the interface.
- Built-in calculator widget alongside the agent, document, and calendar panels.
- Runs as a single-page dashboard — no build step, no frontend framework required.

### 💻 CLI Mode (I do not recommend using this.)
- `litelaw.py` can also be run directly as a standalone command-line agent (without the web dashboard), sharing the same memory store, documents, and safety logic as the web app.

---

## 🛠 Requirements

- **Python** 3.9+
- **[Ollama](https://ollama.com)** installed and running locally
- A pulled local model (default: `gemma3:1b`, configurable via the `LITEMODEL` environment variable or the in-app model picker)
- Linux, macOS, or Windows (developed and tested on Arch Linux)

---

## 📦 Installation

1. **Install Ollama** (if you haven't already) and pull a model:

   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull gemma3:1b
   ollama serve
   ```

   Keep `ollama serve` running in the background (or as a systemd service) — litelaw talks to it at `http://localhost:11434`.

2. **Clone the repository:**

   ```bash
   git clone https://github.com/excellogalihs/litelaw.git
   cd litelaw
   ```

3. **Install Python dependencies:**

   litelaw is designed to be pip-only with no system-level binary dependencies (no Poppler, no Tesseract, etc.).

   ```bash
   pip install flask pypdf python-docx Pillow ddgs
   ```

4. **Run the web dashboard:**

   ```bash
   python3 app.py
   ```

   You should see:

   ```
   ====================================================
    ⬡  litelaw agent web environment runtime dashboard
    Local Access Interface address: http://localhost:5000
   ====================================================
   ```

5. **Open your browser** to [http://localhost:5000](http://localhost:5000) and start chatting with your local agent.

### Optional: CLI mode (I do not recommend using this.)

Run the agent directly in your terminal without the web UI:

```bash
python3 litelaw.py
```

Useful CLI flags:

```bash
python3 litelaw.py --search "your query"      # Web search
python3 litelaw.py --open "https://example.com"  # Open a URL
python3 litelaw.py --doc-list                 # List saved documents
python3 litelaw.py --doc-read <doc_id>        # Read a document
```

### Choosing a model

By default litelaw uses `gemma3:1b` for speed on low-end / CPU-only hardware. To use a different installed Ollama model, either:

- Select it from the model dropdown in the web dashboard.

---

## ⚙️ Configuration

| Setting | Where | Description |
|---|---|---|
| Context size | Settings panel | `num_ctx` sent to Ollama; lower it on weaker CPUs |
| Auto-approve | `litelaw.py` (`AUTO_APPROVE`) | Whether commands run without a manual `(y/n)` confirmation (destructive commands are always blocked regardless) |

All chats, memories, documents, reminders, and settings are stored locally in `litelaw_store.json` next to the app — nothing leaves your machine.

---

## 🗂 Project Structure

```
litelaw/
├── app.py            # Flask web dashboard: routes, streaming, UI, file conversion, calendar
├── litelaw.py         # Core agent engine: Ollama calls, prompt, tools, CLI mode
└── litelaw_store.json # Auto-created local data store (chats, memories, docs, reminders, settings)
```

---

## ⚠️ Disclaimer

litelaw grants a local LLM the ability to run real shell commands on your machine. While it includes guardrails against obviously destructive commands, small local models can still behave unpredictably. Review commands before pointing the agent at anything important, and avoid running it with elevated privileges.
