
# ⬡ litelaw

A lightweight, local computer-automation agent powered by [Ollama](https://ollama.com). Give it a plain-language task, and it plans and executes shell commands on your machine in a loop until the job is done — no cloud API, no API key, fully local.

Available as a **CLI** (`litelaw.py`) or a **web chat UI** (`app.py`) built on top of the same core logic.

## ⚠️ Safety warning

litelaw runs **real shell commands on your machine**, and ships with `AUTO_APPROVE = True` by default — meaning it executes whatever the model decides to run **without asking for confirmation**.

- Only use it in a sandbox, VM, or container, or with a model/task you trust.
- Set `AUTO_APPROVE = False` in `litelaw.py` to require a `(y/n)` prompt before every command.
- Never point it at a task involving sensitive data or production systems.
- The system prompt asks the model to avoid destructive/infinite actions, but this is a *suggestion to the LLM*, not a hard guarantee.

## Features

- 🧠 **Local LLM agent loop** — THOUGHT → ACTION → COMMAND, up to 10 steps per task, using a small local model (default: `gemma3:1b` via Ollama)
- 💻 **Cross-platform command generation** — tailors syntax for Linux, macOS, and Windows (file management, git, process control, diagnostics, networking, etc.)
- 🔁 **Sliding context window** — automatically trims chat history so long sessions don't overload a small local model
- 🖥️ **Two front ends**:
  - `litelaw.py` — interactive terminal REPL
  - `app.py` — Flask-based web chat UI (no changes to `litelaw.py`, just imports it)

## Requirements

- Python 3.9+
- [Ollama](https://ollama.com) installed and running locally
- The configured model pulled, e.g.:
  ```bash
  ollama pull gemma3:1b
  ```
- For the web UI only: `Flask`
  ```bash
  pip install flask
  ```

## Usage

### CLI

```bash
python3 litelaw.py
```

Then type tasks in plain language at the `litelaw ➔` prompt:

```
litelaw ➔ list all .pdf files in my Downloads folder
litelaw ➔ show me git status for the current directory
litelaw ➔ check disk usage and free memory
```

Special commands:
| Command | Effect |
|---|---|
| `clear` | Wipes the current session's chat memory |
| `exit` / `quit` | Ends the session |

### Web UI

```bash
python3 app.py
```

Open **http://localhost:5000** and chat with litelaw in the browser. Each browser session gets its own in-memory conversation history (cookie-based), and the "clear session" button resets it.

## Configuration

Edit the constants at the top of `litelaw.py`:

```python
MODEL = "gemma3:1b"                      # any Ollama-compatible model
OLLAMA_URL = "http://localhost:11434/api/chat"
AUTO_APPROVE = True                      # False = require (y/n) confirmation per command
MAX_CONTEXT_MESSAGES = 20                # sliding window size for chat history
```

## How it works

1. Your task is appended to the conversation and sent to Ollama's `/api/chat` endpoint.
2. The model replies in a strict format:
   ```
   THOUGHT: <reasoning>
   ACTION: RUN_COMMAND
   COMMAND: <shell command>
   ```
   or, when done:
   ```
   THOUGHT: <final reasoning>
   ACTION: FINISHED
   ANSWER: <summary for the user>
   ```
3. `RUN_COMMAND` responses are executed via `subprocess`, and the captured stdout/stderr is fed back to the model as the next turn.
4. This repeats (up to `MAX_STEPS = 10`) until the model returns `FINISHED`, or the step/context limits are hit.

The web UI (`app.py`) reuses `get_system_prompt`, `call_ollama`, `execute_command`, and `parse_response` from `litelaw.py` unmodified, and just renders the same step types (thought / command / output / final / warning / error) as chat bubbles instead of terminal output.

## Project structure

```
litelaw/
├── litelaw.py   # Core agent: system prompt, Ollama client, command execution, CLI REPL
└── app.py       # Flask web UI wrapping the same agent loop
```

## License

No license specified yet — add one (e.g. MIT) if you plan to share or accept contributions.
