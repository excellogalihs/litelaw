#!/usr/bin/env python3
import os
import json
import uuid
from flask import Flask, request, jsonify, render_template_string, session

from litelaw import (
    get_system_prompt,
    call_ollama,
    execute_command,
    parse_response,
    MAX_CONTEXT_MESSAGES,
)

app = Flask(__name__)
app.secret_key = uuid.uuid4().hex

STORE_FILE = "litelaw_store.json"

def load_store():
    """Load data from JSON file or initialize a fresh state."""
    if not os.path.exists(STORE_FILE):
        default_store = {
            "chats": {},
            "memories": [
                "User loves automation and clean terminal configurations.",
                "Always favor modern commands (e.g. printf over echo where applicable)."
            ],
            "documents": {
                "default-doc": {
                    "title": "Scratchpad.txt",
                    "content": "Welcome to your litelaw workspace document editor!\nYou can save temporary data, task definitions, or command templates here."
                }
            }
        }
        save_store(default_store)
        return default_store
    try:
        with open(STORE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"chats": {}, "memories": [], "documents": {}}

def save_store(data):
    """Persist store dictionary cleanly back to disk."""
    with open(STORE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def trim_context(session_messages):
    if len(session_messages) > MAX_CONTEXT_MESSAGES:
        system_prompt = session_messages[0]
        session_messages[:] = [system_prompt] + session_messages[-MAX_CONTEXT_MESSAGES:]

def web_run_agent(user_goal, session_messages, memories):
    """Executes the autonomous terminal workflow loop."""
    steps = []
    session_messages.append({"role": "user", "content": f"Task: {user_goal}"})

    for step in range(10):
        response = call_ollama(session_messages)
        if not response:
            steps.append({
                "type": "error",
                "text": "Could not connect to Ollama. Verify it is running (`ollama serve`)."
            })
            break

        session_messages.append({"role": "assistant", "content": response})

        for line in response.split('\n'):
            if line.startswith("THOUGHT:"):
                steps.append({"type": "thought", "text": line.replace("THOUGHT:", "").strip()})

        action, target = parse_response(response)

        if action == "RUN_COMMAND" and target:
            steps.append({"type": "command", "text": target})
            cmd_output = execute_command(target)
            steps.append({"type": "output", "text": cmd_output.strip()})
            session_messages.append({"role": "user", "content": f"Command output:\n{cmd_output}"})
        elif action == "FINISHED":
            steps.append({"type": "final", "text": target})
            break
        else:
            steps.append({
                "type": "warning",
                "text": "Formatting misalignment detected; adjusting agent constraints."
            })
            session_messages.append({
                "role": "user",
                "content": "Invalid layout. Return your move strictly using ACTION: RUN_COMMAND or ACTION: FINISHED."
            })
    else:
        steps.append({"type": "error", "text": "Reached step threshold limit before closure."})

    trim_context(session_messages)
    return steps

@app.route("/")
def index():
    return render_template_string(PAGE_HTML)

@app.route("/api/init", methods=["GET"])
def initialize_workspace():
    """Flashes out entire synchronized store data to frontend sidebar."""
    store = load_store()
    chat_list = [{"id": cid, "title": c["title"]} for cid, c in store["chats"].items()]
    doc_list = [{"id": did, "title": d["title"]} for did, d in store["documents"].items()]
    return jsonify({
        "chats": chat_list,
        "memories": store["memories"],
        "documents": doc_list
    })

@app.route("/api/chat/new", methods=["POST"])
def create_new_chat():
    store = load_store()
    chat_id = uuid.uuid4().hex
    
    # Pre-inject system prompt bundled with current persistent memories
    store["chats"][chat_id] = {
        "title": "Untitled Operations Thread",
        "messages": [{"role": "system", "content": get_system_prompt(store["memories"])}]
    }
    save_store(store)
    return jsonify({"chat_id": chat_id, "title": store["chats"][chat_id]["title"]})

@app.route("/api/chat/get", methods=["GET"])
def get_chat_history():
    chat_id = request.args.get("chat_id")
    store = load_store()
    if chat_id not in store["chats"]:
        return jsonify({"error": "Thread expired or absent"}), 404
    
    # Filter structural system records away from UI chat view nodes
    visible_steps = []
    raw_msgs = store["chats"][chat_id]["messages"]
    
    # Parse existing history back into interactive client steps
    for idx, m in enumerate(raw_msgs):
        if m["role"] == "user" and m["content"].startswith("Task: "):
            visible_steps.append({"type": "user_msg", "text": m["content"].replace("Task: ", "")})
        elif m["role"] == "assistant":
            resp = m["content"]
            for line in resp.split('\n'):
                if line.startswith("THOUGHT:"):
                    visible_steps.append({"type": "thought", "text": line.replace("THOUGHT:", "").strip()})
            
            # Look at subsequent indices for command execution outputs
            action, target = parse_response(resp)
            if action == "RUN_COMMAND":
                visible_steps.append({"type": "command", "text": target})
                if idx + 1 < len(raw_msgs) and raw_msgs[idx+1]["role"] == "user" and raw_msgs[idx+1]["content"].startswith("Command output:\n"):
                    out_text = raw_msgs[idx+1]["content"].replace("Command output:\n", "")
                    visible_steps.append({"type": "output", "text": out_text})
            elif action == "FINISHED":
                visible_steps.append({"type": "final", "text": target})
                
    return jsonify({"steps": visible_steps})

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    chat_id = data.get("chat_id")
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"steps": [{"type": "error", "text": "Empty command syntax query submission."}]})

    store = load_store()
    
    # If client lacks an active session ID or thread got deleted, spin a new one up
    if not chat_id or chat_id not in store["chats"]:
        chat_id = uuid.uuid4().hex
        store["chats"][chat_id] = {
            "title": message[:32] + "..." if len(message) > 32 else message,
            "messages": [{"role": "system", "content": get_system_prompt(store["memories"])}]
        }
    elif store["chats"][chat_id]["title"] == "Untitled Operations Thread":
        store["chats"][chat_id]["title"] = message[:32] + "..." if len(message) > 32 else message

    session_messages = store["chats"][chat_id]["messages"]
    steps = web_run_agent(message, session_messages, store["memories"])
    
    store["chats"][chat_id]["messages"] = session_messages
    save_store(store)
    
    return jsonify({"steps": steps, "chat_id": chat_id, "title": store["chats"][chat_id]["title"]})

# --- Memory Routes ---
@app.route("/api/memories/add", methods=["POST"])
def add_memory():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Empty string context"}), 400
    store = load_store()
    if text not in store["memories"]:
        store["memories"].append(text)
        save_store(store)
    return jsonify({"ok": True, "memories": store["memories"]})

@app.route("/api/memories/delete", methods=["POST"])
def delete_memory():
    data = request.get_json(force=True) or {}
    index = data.get("index")
    store = load_store()
    if index is not None and 0 <= index < len(store["memories"]):
        store["memories"].pop(index)
        save_store(store)
    return jsonify({"ok": True, "memories": store["memories"]})

# --- Document Workspaces Routes ---
@app.route("/api/documents/get", methods=["GET"])
def get_document():
    doc_id = request.args.get("doc_id")
    store = load_store()
    if doc_id not in store["documents"]:
        return jsonify({"error": "File object not found"}), 404
    return jsonify(store["documents"][doc_id])

@app.route("/api/documents/save", methods=["POST"])
def save_document():
    data = request.get_json(force=True) or {}
    doc_id = data.get("doc_id")
    title = data.get("title", "Untitled.txt").strip() or "Untitled.txt"
    content = data.get("content", "")
    
    store = load_store()
    if not doc_id:
        doc_id = uuid.uuid4().hex
        
    store["documents"][doc_id] = {"title": title, "content": content}
    save_store(store)
    return jsonify({"ok": True, "doc_id": doc_id, "title": title})

@app.route("/api/documents/new", methods=["POST"])
def new_document():
    store = load_store()
    doc_id = uuid.uuid4().hex
    store["documents"][doc_id] = {"title": "New_Buffer.txt", "content": ""}
    save_store(store)
    return jsonify({"doc_id": doc_id, "title": "New_Buffer.txt"})

PAGE_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>litelaw AI Workspace</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
@font-face {
  font-family: 'JetBrainsMono Nerd Font';
  src: url('https://cdn.jsdelivr.net/gh/ryanoasis/nerd-fonts@v3.2.1/patched-fonts/JetBrainsMono/Ligatures/Regular/JetBrainsMonoNerdFontMono-Regular.ttf') format('truetype');
  font-weight: 400; font-style: normal; font-display: swap;
}
:root{
  --bg-0:#07040f;
  --bg-1:#0d0620;
  --bg-2:#160a33;
  --panel:#120a26cc;
  --panel-solid:#140b28;
  --sidebar-bg:#090514;
  --border:#3a2470;
  --border-soft:#2a1a52;
  --violet-1:#a78bfa;
  --violet-2:#8b5cf6;
  --violet-3:#7c3aed;
  --magenta:#e879f9;
  --cyan:#67e8f9;
  --text-0:#ede9fe;
  --text-1:#c4b5fd;
  --text-dim:#8a7cad;
  --green:#4ade80;
  --red:#f87171;
  --yellow:#facc15;
  --mono: 'JetBrainsMono Nerd Font', 'JetBrains Mono', ui-monospace, monospace;
}
*{ box-sizing:border-box; }
html,body{
  height:100%; margin:0; font-family: var(--mono);
  background: var(--bg-0); color: var(--text-0); overflow:hidden;
}
.nebula{
  position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    radial-gradient(ellipse 900px 600px at 15% 15%, rgba(139,92,246,0.15), transparent 60%),
    radial-gradient(ellipse 800px 700px at 85% 25%, rgba(232,121,249,0.12), transparent 60%),
    linear-gradient(180deg, var(--bg-1) 0%, var(--bg-0) 100%);
}
#stars{ position:fixed; inset:0; z-index:0; pointer-events:none; }

.app-frame{
  position:relative; z-index:1; height:100vh;
  display:flex; flex-direction:column;
}
header{
  display:flex; align-items:center; justify-content:space-between;
  padding:12px 20px; border-bottom:1px solid var(--border-soft);
  background: rgba(20,11,40,0.85); backdrop-filter: blur(12px);
}
.brand{ display:flex; align-items:center; gap:12px; }
.brand-mark{
  width:32px; height:32px; border-radius:8px;
  display:flex; align-items:center; justify-content:center;
  background: radial-gradient(circle at 30% 30%, var(--violet-1), var(--violet-3) 70%);
  box-shadow: 0 0 14px rgba(139,92,246,0.5); font-size:16px;
}
.brand-text h1{
  margin:0; font-size:16px; font-weight:800; letter-spacing:0.5px;
  background: linear-gradient(90deg, var(--violet-1), var(--magenta));
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
.brand-text span{ display:block; font-size:10px; color:var(--text-dim); }

.workspace-layout{ display:flex; flex:1; overflow:hidden; }

/* --- SIDEBAR PANEL --- */
.sidebar{
  width:280px; background: var(--sidebar-bg);
  border-right:1px solid var(--border-soft);
  display:flex; flex-direction:column; gap:20px; padding:16px; overflow-y:auto;
}
.sidebar-section-title{
  font-size:10.5px; text-transform:uppercase; color:var(--text-dim);
  letter-spacing:1px; margin-bottom:8px; font-weight:700;
  display:flex; align-items:center; justify-content:between;
}
.sidebar-btn{
  width:100%; font-family:var(--mono); text-align:left;
  background:rgba(139,92,246,0.06); border:1px solid var(--border-soft);
  color:var(--text-1); padding:9px 12px; border-radius:8px;
  font-size:12px; cursor:pointer; transition: all .15s ease;
  display:flex; align-items:center; gap:8px; margin-bottom:6px;
}
.sidebar-btn:hover, .sidebar-btn.active{
  background:rgba(139,92,246,0.16); border-color: var(--violet-1); color:#fff;
}
.history-list, .doc-list { 
  display: flex; 
  flex-direction: column; 
  gap: 4px; 
  max-height: 160px;
  width: 100%; 
  overflow-y: auto;
  overflow-x: hidden; 

  /* Thin, themed scrollbar (matches chat-scroller) */
  -ms-overflow-style: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(167,139,250,0.35) transparent;
}

.history-list::-webkit-scrollbar,
.doc-list::-webkit-scrollbar {
  width: 6px;
}
.history-list::-webkit-scrollbar-track,
.doc-list::-webkit-scrollbar-track {
  background: transparent;
}
.history-list::-webkit-scrollbar-thumb,
.doc-list::-webkit-scrollbar-thumb {
  background: rgba(167,139,250,0.35);
  border-radius: 8px;
}
.history-list::-webkit-scrollbar-thumb:hover,
.doc-list::-webkit-scrollbar-thumb:hover {
  background: rgba(167,139,250,0.6);
}
.list-item-link {
  display: block;           /* Necessary to enforce clipping and vertical block flow */
  width: 100%;              /* Forces text to wrap/clip at exact container boundary */
  flex-shrink: 0;           /* Prevents flex column from squishing items to fit — lets list overflow & scroll */
  padding: 6px 10px; 
  font-size: 11.5px; 
  border-radius: 6px; 
  cursor: pointer;
  white-space: nowrap; 
  overflow: hidden; 
  text-overflow: ellipsis;  /* Puts '...' safely at the edge of the sidebar */
  color: var(--text-dim); 
  transition: all 0.12s ease;
}

.list-item-link:hover, .list-item-link.active {
  background: rgba(167,139,250,0.08); 
  color: var(--text-0);
}
/* --- MAIN INTERACTIVE VIEW AREA --- */
.main-stage{ flex:1; display:flex; flex-direction:column; background:rgba(7,4,15,0.4); overflow:hidden; }
.stage-panel{ display:none; flex:1; flex-direction:column; overflow:hidden; }
.stage-panel.active{ display:flex; min-height:0; }

/* CHAT PANEL SCROLLER */
.chat-scroller { 
  flex: 1; 
  min-height: 0;              /* Prevents flex item from refusing to shrink/scroll */
  width: 100%;
  overflow-y: auto;          /* Enables natural scroll actions */
  overflow-x: hidden;
  padding: 24px 0; 
  display: flex;
  flex-direction: column;
  position: relative;

  /* Thin, themed scrollbar instead of hiding it entirely */
  -ms-overflow-style: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(167,139,250,0.35) transparent;
}

.chat-scroller::-webkit-scrollbar {
  width: 8px;
}
.chat-scroller::-webkit-scrollbar-track {
  background: transparent;
}
.chat-scroller::-webkit-scrollbar-thumb {
  background: rgba(167,139,250,0.35);
  border-radius: 8px;
}
.chat-scroller::-webkit-scrollbar-thumb:hover {
  background: rgba(167,139,250,0.6);
}

/* Jump-to-latest button, shown when the user has scrolled away from the bottom */
.scroll-to-bottom-btn {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: none;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid var(--border-soft);
  background: rgba(20,11,40,0.92);
  backdrop-filter: blur(8px);
  color: var(--text-1);
  font-family: var(--mono);
  font-size: 11px;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(0,0,0,0.35);
  z-index: 5;
}
.scroll-to-bottom-btn.visible { display: flex; }
.scroll-to-bottom-btn:hover { background: rgba(139,92,246,0.18); }

/* BUBBLES CONTAINER */
.chat-container { 
  width: 100%;
  max-width: 800px; 
  margin: 0 auto; 
  padding: 0 20px; 
  display: flex; 
  flex-direction: column; 
  gap: 16px;
  flex-grow: 1;             /* Forces layout alignment engine to expand the inner layer */
}
.row{ display:flex; width:100%; }
.row.user{ justify-content:flex-end; }
.row.assistant{ justify-content:flex-start; }
.bubble{ max-width:82%; padding:11px 15px; border-radius:12px; font-size:13px; line-height:1.5; white-space:pre-wrap; }
.bubble.user{
  background: linear-gradient(135deg, var(--violet-3), #5b21b6); color:#fff;
  border: 1px solid rgba(167,139,250,0.3); border-bottom-right-radius:2px;
}
.bubble.final{ background: var(--panel-solid); border:1px solid var(--border-soft); border-bottom-left-radius:2px; }
.bubble.final::before{ content:"⬡ litelaw response"; display:block; font-size:10px; color:var(--violet-1); margin-bottom:4px; font-weight:700; }
.thought{ max-width:82%; font-size:11.5px; color:var(--text-dim); font-style:italic; padding:2px; }
.thought::before{ content:"✧ "; color:var(--violet-1); }

.term-block{ width:82%; border-radius:8px; overflow:hidden; border:1px solid var(--border-soft); background:#05020a; }
.term-head{ display:flex; align-items:center; gap:6px; padding:6px 12px; background:rgba(139,92,246,0.06); font-size:10px; color:var(--text-dim); }
.term-dots span{ width:6px; height:6px; border-radius:50%; display:inline-block; background:#3a2470; }
.term-body{ padding:10px 12px; font-size:12px; white-space:pre-wrap; }
.term-body.command{ color:var(--cyan); }
.term-body.command::before{ content:"$ "; color:var(--violet-1); }
.term-body.output{ color:var(--text-1); }

/* MEMORY PANEL */
.memory-workspace, .editor-workspace{ max-width:800px; width:100%; margin:30px auto; padding:0 20px; display:flex; flex-direction:column; gap:20px; }
.memory-input-group{ display:flex; gap:10px; }
.input-field{
  flex:1; background:rgba(139,92,246,0.06); border:1px solid var(--border);
  border-radius:8px; padding:10px 14px; color:#fff; font-family:var(--mono); font-size:13px;
}
.memory-card-list{ display:flex; flex-direction:column; gap:10px; margin-top:10px; }
.memory-item{
  background:var(--panel-solid); border:1px solid var(--border-soft);
  padding:12px 16px; border-radius:8px; display:flex; align-items:center; justify-content:space-between; font-size:12.5px;
}
.delete-btn{ background:transparent; border:none; color:var(--red); cursor:pointer; font-family:var(--mono); }

/* EDITOR WORKSPACE */
.editor-meta{ display:flex; gap:12px; width:100%; }
.editor-textarea{
  flex:1; min-height:400px; background: #05020a; border:1px solid var(--border-soft);
  border-radius:8px; padding:16px; color:var(--text-0); font-family:var(--mono); font-size:13px; line-height:1.6; resize:none;
}

/* CHAT CONTROLS WRAPPER */
.input-wrap{ border-top:1px solid var(--border-soft); padding:14px 20px; background:rgba(9,5,20,0.7); }
.input-inner{ max-width:800px; margin:0 auto; display:flex; align-items:center; gap:10px; background:rgba(139,92,246,0.04); border:1px solid var(--border); border-radius:10px; padding:8px 12px; }
textarea#msg{ flex:1; resize:none; background:transparent; border:none; outline:none; color:#fff; font-family:var(--mono); font-size:13px; }
.send-btn{ width:34px; height:34px; border-radius:8px; border:none; cursor:pointer; background:linear-gradient(135deg, var(--violet-1), var(--violet-3)); color:#fff; display:flex; align-items:center; justify-content:center; }

.empty-state{ margin-top:10vh; text-align:center; color:var(--text-dim); }
.empty-state h2{ color:#fff; font-size:16px; margin-bottom:4px; }
</style>
</head>
<body>
<div class="nebula"></div>
<canvas id="stars"></canvas>

<div class="app-frame">
  <header>
    <div class="brand">
      <div class="brand-mark">⬡</div>
      <div class="brand-text">
        <h1>litelaw</h1>
        <span>automation environment & control agent</span>
      </div>
    </div>
    <div style="font-size:11px; color:var(--green);"><span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--green); margin-right:4px;"></span> agent synchronized</div>
  </header>

  <div class="workspace-layout">
    <div class="sidebar">
      <button class="sidebar-btn" id="newChatBtn">➔ + New Context Thread</button>
      
      <div>
        <div class="sidebar-section-title">Active Configurations</div>
        <button class="sidebar-btn" id="memVaultTabLink">✦ Long-Term Memory</button>
        <button class="sidebar-btn" id="docEditorTabLink">📝 Document Editor</button>
      </div>

      <div>
        <div class="sidebar-section-title">Execution History</div>
        <div class="history-list" id="historyContainer"></div>
      </div>

      <div>
        <div class="sidebar-section-title">Saved Buffers</div>
        <div class="doc-list" id="savedDocsContainer"></div>
      </div>
    </div>

    <div class="main-stage">
      
      <div class="stage-panel active" id="chatPanel">
        <div class="chat-scroller" id="chatScroller">
          <div class="chat-container" id="chatContainer">
            <div class="empty-state" id="emptyState">
              <h2>Autonomous Terminal Workspace</h2>
              <p style="font-size:12px;">Provide goals in standard plaintext. The engine compiles and acts locally.</p>
            </div>
          </div>
          <button class="scroll-to-bottom-btn" id="scrollToBottomBtn">↓ Jump to latest</button>
        </div>
        <div class="input-wrap">
          <div class="input-inner">
            <textarea id="msg" rows="1" placeholder="Instruct agent..."></textarea>
            <button class="send-btn" id="sendBtn">➤</button>
          </div>
        </div>
      </div>

      <div class="stage-panel" id="memoryPanel">
        <div class="memory-workspace">
          <h3>🧠 Core Long-Term Memory Guard</h3>
          <p style="font-size:12px; color:var(--text-dim); margin:0 0 10px 0;">Statements managed here persist across engine restarts and lock rules or preferences natively into the compilation logic loop.</p>
          <div class="memory-input-group">
            <input type="text" id="memoryInput" class="input-field" placeholder="Append context constraint rule...">
            <button class="sidebar-btn" id="addMemoryBtn" style="width:auto; margin:0;">Add Memory</button>
          </div>
          <div class="memory-card-list" id="memoryCardList"></div>
        </div>
      </div>

      <div class="stage-panel" id="editorPanel">
        <div class="editor-workspace">
          <h3>📝 Dynamic Document Buffer Workspace</h3>
          <div class="editor-meta">
            <input type="text" id="docTitle" class="input-field" placeholder="File name context (e.g. log.txt)">
            <button class="sidebar-btn" id="saveDocBtn" style="width:auto; margin:0;">💾 Commit Save File</button>
            <button class="sidebar-btn" id="newDocBtn" style="width:auto; margin:0; background:rgba(255,255,255,0.04)">+ New Doc</button>
          </div>
          <textarea id="docContent" class="editor-textarea" placeholder="Load or write temporary strings here..."></textarea>
        </div>
      </div>

    </div>
  </div>
</div>

<script>
// --- Canvas Starscape Logic ---
const canvas = document.getElementById('stars'); const ctx = canvas.getContext('2d');
let stars = [];
function resizeCanvas(){
  canvas.width = window.innerWidth; canvas.height = window.innerHeight; stars = [];
  const count = Math.floor((canvas.width * canvas.height) / 11000);
  for(let i=0;i<count;i++) stars.push({x:Math.random()*canvas.width, y:Math.random()*canvas.height, r:Math.random()*1.2+0.2, a:Math.random(), d:(Math.random()*0.01)+0.002});
}
function drawStars(){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  for(const s of stars){ s.a += s.d; if(s.a>1||s.a<0) s.d*=-1; ctx.beginPath(); ctx.fillStyle=`rgba(196,181,253,${Math.abs(Math.sin(s.a))})`; ctx.arc(s.x, s.y, s.r, 0, Math.PI*2); ctx.fill(); }
  requestAnimationFrame(drawStars);
}
window.addEventListener('resize', resizeCanvas); resizeCanvas(); drawStars();

// --- Core App Management Workspace Architecture ---
let currentChatId = "";
let currentDocId = "default-doc";

const chatContainer = document.getElementById('chatContainer');
const emptyState = document.getElementById('emptyState');
const msgEl = document.getElementById('msg');
const sendBtn = document.getElementById('sendBtn');
const chatScroller = document.getElementById('chatScroller');
const scrollToBottomBtn = document.getElementById('scrollToBottomBtn');

// --- Smart Auto-Scroll ---
// Only snap to the bottom automatically if the user is already near it.
// If they've scrolled up to read earlier messages, new steps won't yank them back.
const NEAR_BOTTOM_PX = 120;
function isNearBottom() {
  return (chatScroller.scrollHeight - chatScroller.scrollTop - chatScroller.clientHeight) < NEAR_BOTTOM_PX;
}
function scrollToBottom(force = false) {
  if (force || isNearBottom()) {
    chatScroller.scrollTop = chatScroller.scrollHeight;
  }
  updateScrollButton();
}
function updateScrollButton() {
  scrollToBottomBtn.classList.toggle('visible', !isNearBottom() && chatScroller.scrollHeight > chatScroller.clientHeight + 40);
}
chatScroller.addEventListener('scroll', updateScrollButton);
scrollToBottomBtn.addEventListener('click', () => scrollToBottom(true));
window.addEventListener('resize', updateScrollButton);

// Workspace View Toggles
function switchView(targetPanelId, triggerElement=null) {
  document.querySelectorAll('.stage-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.sidebar-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.list-item-link').forEach(l => l.classList.remove('active'));
  
  document.getElementById(targetPanelId).classList.add('active');
  if(triggerElement) triggerElement.classList.add('active');
}

document.getElementById('memVaultTabLink').addEventListener('click', (e) => {
  switchView('memoryPanel', e.currentTarget);
  loadMemoryWorkspace();
});
document.getElementById('docEditorTabLink').addEventListener('click', (e) => {
  switchView('editorPanel', e.currentTarget);
  loadDocument(currentDocId);
});

// Sync Core Metadata Store View Left Sidebar
async function syncWorkspaceManifest() {
  const res = await fetch('/api/init');
  const data = await res.json();
  
  // Update Executed Threads History List
  const histContainer = document.getElementById('historyContainer');
  histContainer.innerHTML = "";
  data.chats.forEach(c => {
    const link = document.createElement('div');
    link.className = `list-item-link ${c.id === currentChatId ? 'active' : ''}`;
    link.textContent = "⬡ " + c.title;
    link.addEventListener('click', () => selectChatThread(c.id));
    histContainer.appendChild(link);
  });

  // Update System Buffer Document Collection
  const docContainer = document.getElementById('savedDocsContainer');
  docContainer.innerHTML = "";
  data.documents.forEach(d => {
    const link = document.createElement('div');
    link.className = `list-item-link ${d.id === currentDocId ? 'active' : ''}`;
    link.textContent = "📝 " + d.title;
    link.addEventListener('click', () => {
      currentDocId = d.id;
      switchView('editorPanel', document.getElementById('docEditorTabLink'));
      loadDocument(d.id);
    });
    docContainer.appendChild(link);
  });
}

// Select/Load Chat Context History Thread
async function selectChatThread(chatId) {
  currentChatId = chatId;
  switchView('chatPanel');
  if(emptyState) emptyState.style.display = 'none';
  chatContainer.innerHTML = "";
  
  const res = await fetch(`/api/chat/get?chat_id=${chatId}`);
  if(res.ok) {
    const data = await res.json();
    data.steps.forEach(step => addStepNodeToStage(step));
    scrollToBottom(true);
  }
  syncWorkspaceManifest();
}

// Spin a New Context State
document.getElementById('newChatBtn').addEventListener('click', async () => {
  const res = await fetch('/api/chat/new', {method:'POST'});
  const data = await res.json();
  currentChatId = data.chat_id;
  if(emptyState) emptyState.style.display = 'none';
  chatContainer.innerHTML = `
    <div class="empty-state">
      <h2>Fresh Operational Thread State Enabled</h2>
      <p style="font-size:12px;">Long-term context memory configurations are integrated dynamically into this agent frame.</p>
    </div>`;
  syncWorkspaceManifest();
  switchView('chatPanel');
});

// UI Node Visual Injection Mechanics
function addStepNodeToStage(step) {
  const row = document.createElement('div');
  row.className = 'row assistant';

  if(step.type === 'user_msg') {
    row.className = 'row user';
    row.innerHTML = `<div class="bubble user"></div>`;
    row.querySelector('.bubble').textContent = step.text;
  } else if(step.type === 'thought'){
    row.innerHTML = `<div class="thought"></div>`;
    row.querySelector('.thought').textContent = step.text;
  } else if(step.type === 'command'){
    row.innerHTML = `<div class="term-block"><div class="term-head"><span class="term-dots"><span></span></span> operational syntax command execution</div><div class="term-body command"></div></div>`;
    row.querySelector('.term-body').textContent = step.text;
  } else if(step.type === 'output'){
    row.innerHTML = `<div class="term-block"><div class="term-head"><span class="term-dots"><span></span></span> runtime captured environment buffer</div><div class="term-body output"></div></div>`;
    row.querySelector('.term-body').textContent = step.text || '(empty standard output buffer captured)';
  } else if(step.type === 'final'){
    row.innerHTML = `<div class="bubble final"></div>`;
    row.querySelector('.bubble').textContent = step.text;
  } else if(step.type === 'warning'){
    row.innerHTML = `<div style="color:var(--yellow); font-size:11px; padding:4px;">⚠ ${step.text}</div>`;
  } else if(step.type === 'error'){
    row.innerHTML = `<div style="color:var(--red); font-size:11px; padding:4px;">✕ ${step.text}</div>`;
  }
  chatContainer.appendChild(row);
  scrollToBottom();
}

// Action Trigger Agent Transaction pipeline
async function dispatchMessage(){
  const text = msgEl.value.trim();
  if(!text) return;
  msgEl.value = ''; msgEl.style.height = 'auto'; sendBtn.disabled = true;

  if (emptyState) emptyState.style.display = 'none';
  addStepNodeToStage({type: 'user_msg', text: text});
  scrollToBottom(true);

  // Structural Thinking Indicator Component Inject
  const thinkRow = document.createElement('div');
  thinkRow.className = 'row assistant'; thinkRow.id = 'agentPulseIndicator';
  thinkRow.innerHTML = `<div style="font-size:12px; color:var(--text-dim); padding:4px;">🤖 thinking...</div>`;
  chatContainer.appendChild(thinkRow);
  scrollToBottom(true);

  try {
    const res = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: text, chat_id: currentChatId})
    });
    const data = await res.json();
    currentChatId = data.chat_id;
    
    const pulse = document.getElementById('agentPulseIndicator'); if(pulse) pulse.remove();

    for(const step of (data.steps || [])){
      addStepNodeToStage(step);
      await new Promise(r => setTimeout(r, 60));
    }
    syncWorkspaceManifest();
  } catch(e) {
    const pulse = document.getElementById('agentPulseIndicator'); if(pulse) pulse.remove();
    addStepNodeToStage({type:'error', text: 'Lost interface sync pipeline connection: ' + e});
  } finally {
    sendBtn.disabled = false; msgEl.focus();
  }
}

sendBtn.addEventListener('click', dispatchMessage);
msgEl.addEventListener('keydown', (e) => { if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); dispatchMessage(); } });

// --- Long-Term Memory View Handlers ---
async function loadMemoryWorkspace() {
  const res = await fetch('/api/init');
  const data = await res.json();
  const listEl = document.getElementById('memoryCardList');
  listEl.innerHTML = "";
  
  data.memories.forEach((m, idx) => {
    const item = document.createElement('div');
    item.className = "memory-item";
    item.innerHTML = `<span>${m}</span><button class="delete-btn" data-idx="${idx}">✕ Delete</button>`;
    item.querySelector('.delete-btn').addEventListener('click', async (e) => {
      const targetIdx = e.currentTarget.getAttribute('data-idx');
      const delRes = await fetch('/api/memories/delete', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({index: parseInt(targetIdx)})
      });
      if(delRes.ok) loadMemoryWorkspace();
    });
    listEl.appendChild(item);
  });
}

document.getElementById('addMemoryBtn').addEventListener('click', async () => {
  const input = document.getElementById('memoryInput');
  const text = input.value.strip ? input.value.strip() : input.value.trim();
  if(!text) return;
  const res = await fetch('/api/memories/add', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({text: text})
  });
  if(res.ok) { input.value = ""; loadMemoryWorkspace(); }
});

// --- Document Workspace Tool Handlers ---
async function loadDocument(docId) {
  currentDocId = docId;
  const res = await fetch(`/api/documents/get?doc_id=${docId}`);
  if(res.ok) {
    const data = await res.json();
    document.getElementById('docTitle').value = data.title;
    document.getElementById('docContent').value = data.content;
  }
}

document.getElementById('saveDocBtn').addEventListener('click', async () => {
  const title = document.getElementById('docTitle').value;
  const content = document.getElementById('docContent').value;
  const res = await fetch('/api/documents/save', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({doc_id: currentDocId, title: title, content: content})
  });
  if(res.ok) { syncWorkspaceManifest(); alert("Buffer state committed successfully."); }
});

document.getElementById('newDocBtn').addEventListener('click', async () => {
  const res = await fetch('/api/documents/new', {method:'POST'});
  const data = await res.json();
  currentDocId = data.doc_id;
  loadDocument(data.doc_id);
  syncWorkspaceManifest();
});

// Initialize Framework Workspace state configurations on startup
syncWorkspaceManifest();
switchView('chatPanel');
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("====================================================")
    print(" ⬡  litelaw agent web environment runtime dashboard")
    print(" Local Access Interface address: http://localhost:5000")
    print("====================================================")
    app.run(host="0.0.0.0", port=5000, debug=False)
