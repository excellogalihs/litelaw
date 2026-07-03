![litelaw banner](banner.jpeg)
# litelaw

**litelaw** is a lightweight, fully local AI agent and workspace dashboard. It runs entirely on your machine using [Ollama](https://ollama.com) (default model: `gemma3:1b`), and wraps a terminal-automation agent in a Flask web dashboard with a chat interface, document editor, calendar/reminders, calculator, and file converter — all with zero cloud dependency.

`app.py` is a Flask app that serves a single-page browser dashboard with step-by-step agent output, persistent chats, a document workspace, and a few built-in utility tools. The underlying agent logic lives in `litelaw.py`, which `app.py` imports and drives.

---

## Features

### 🤖 Autonomous terminal agent
- Runs a `THOUGHT → ACTION → COMMAND/ANSWER` loop against a local Ollama model (`gemma3:1b` by default).
- The model can issue `RUN_COMMAND` steps that execute real shell commands via `subprocess`, observe the output, and iterate — up to 10 steps per task before it's forced to stop.
- Built-in loop detection: if the same command repeats 2–3 times in a row, litelaw warns the model and eventually forces it to finish, preventing infinite command loops.
- Guards against a common small-model failure mode: using `touch` when the user actually wants text written to a file (nudges the model toward `printf`/`echo` instead).
- Strips conversational sign-offs ("thanks", "goodbye", etc.) and echoed file contents out of the model's final answer so responses stay clean.
- OS-aware prompting — the system prompt adapts command syntax (e.g. `pkill` vs `taskkill`) based on `platform.system()`.

### 💬 Web chat dashboard
- Multi-chat sessions persisted to a local JSON store (`litelaw_store.json`), each with its own trimmed message history (capped at `MAX_CONTEXT_MESSAGES = 20` to keep the context window small for low-resource hardware).
- Chat titles auto-generate from the first message.
- Visualized step-by-step agent output in the browser: thoughts, commands, command output, warnings, and the final answer.

### 🧠 Persistent memory
- A simple list of "memories" (facts/preferences) is stored and injected into every system prompt, so the agent can remember user preferences across sessions (e.g. "prefer `printf` over `echo`").
- Add/delete memories via the dashboard or the store directly.

### 📄 Document workspace
- Built-in document editor with create / read / update / delete / import / export, synced to the JSON store. The agent itself can call the same document operations internally when a task requires editing a document, rather than falling back to raw shell commands.
- AI-assisted document editing (`/api/chat/doc`) — give an instruction and the model rewrites the full document, with aggressive response-cleaning logic to strip preambles like "Here's the corrected version:" that small models tend to add despite instructions.
- Import/export documents as plain text files from disk.

### 📅 Calendar & reminders
- Simple date-keyed reminders stored server-side, with a calendar UI, add/delete, and desktop notifications (via the browser Notification API) plus an in-app banner for today's reminders.
- Polls the backend every 60 seconds to stay in sync.

### 🔎 Live web search
- The agent can search the web (backed by the `ddgs` / DuckDuckGo Search package) and open URLs in the system's default browser as part of completing a task, instead of relying on `curl` or other raw commands.

### 🧮 Utility tools (in the dashboard)
- **Calculator** — simple expression calculator UI.
- **File converter** — converts between common formats directly in the browser via a Flask backend:
  - PDF → TXT, DOCX → TXT, PDF → DOCX
  - PNG ⇄ JPEG, image → PDF

---

## Architecture

```
litelaw.py   — Core agent logic: system prompt, Ollama client, command execution,
                document store helpers, web search.
app.py       — Flask web app: imports litelaw.py, adds a Server-rendered single-page
                dashboard (chat, documents, calendar, calculator, converter), and
                exposes it all as JSON API routes.
litelaw_store.json — Local JSON "database": chats, memories, documents, reminders.
                       Auto-created on first run.
```

`app.py` imports the core agent functions from `litelaw.py` (`get_system_prompt`, `call_ollama`, `execute_command`, `parse_response`, `doc_write`) and drives them from Flask routes, reading and writing the same JSON store.

### Agent response format
The model is constrained to respond in one of two strict formats:

```
THOUGHT: <reasoning>
ACTION: RUN_COMMAND
COMMAND: <shell command>
```

```
THOUGHT: <reasoning>
ACTION: FINISHED
ANSWER: <summary for the user>
```

`parse_response()` extracts the action/command/answer from this format, and the agent loop (`web_run_agent` / `run_agent`) drives execution until `FINISHED` or a 10-step safety cap is hit.

---

## Requirements

- Python 3
- [Ollama](https://ollama.com) running locally with a pulled model (default `gemma3:1b`):
  ```bash
  ollama pull gemma3:1b
  ```
- Python packages:
  ```bash
  pip install flask pypdf python-docx pillow ddgs
  ```

> litelaw favors pip-only, zero-system-dependency packages where possible so it stays easy to run on modest, CPU-only hardware.

---

## Usage

```bash
python3 app.py
```
Then open **http://127.0.0.1:5000**. The dashboard runs on `0.0.0.0:5000` by default.

From there you can:
- Chat with the agent and watch it plan, run commands, and report back in the **Chat** panel.
- Create, edit, import/export, and AI-edit text documents in the **Document Editor** panel.
- Add and manage date-based reminders in the **Calendar** panel.
- Do quick math in the **Calculator** panel.
- Convert files (PDF/DOCX/images) in the **File Converter** panel.
- Add/remove persistent memories that get injected into every chat's system prompt.

---

## Configuration

Set at the top of `litelaw.py`:

| Setting | Default | Description |
|---|---|---|
| `MODEL` | `"gemma3:1b"` | Ollama model name |
| `OLLAMA_URL` | `"http://localhost:11434/api/chat"` | Ollama chat API endpoint |
| `AUTO_APPROVE` | `True` | Controls whether commands execute automatically; the web dashboard runs with this enabled, so model-issued commands execute without a confirmation step |
| `MAX_CONTEXT_MESSAGES` | `20` | Caps stored conversation length per chat to control context window size |

---

## Notes & known limitations

- **No sandboxing**: commands run directly on the host via `subprocess.run(..., shell=True)`. `AUTO_APPROVE = True` means the web dashboard executes model-issued commands without a confirmation step — treat this as a local, trusted-environment tool, not something to expose beyond `localhost`.
- **Small-model quirks**: `gemma3:1b` is fast and lightweight but prone to instruction-drift (e.g. adding conversational preambles, misusing `touch`, echoing file content into answers). Several layers of the codebase (`_clean_answer`, preamble-stripping in `/api/chat/doc`, the touch-misuse guard) exist specifically to compensate for this.
- The JSON store (`litelaw_store.json`) is a flat file with no locking — fine for single-user local use, not concurrency-safe.
