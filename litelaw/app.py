#!/usr/bin/env python3
"""
litelaw web UI — a Flask front-end for the litelaw local automation agent.

This file does NOT modify litelaw.py. It imports the existing, unmodified
functions (get_system_prompt, call_ollama, execute_command, parse_response,
MAX_CONTEXT_MESSAGES) and wraps them in a small web server + chat UI.

Run with:
    python3 app.py

Then open:
    http://localhost:5000
"""
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
app.secret_key = uuid.uuid4().hex  # local-only tool, random per-run secret is fine

MAX_STEPS = 10

# In-memory session store: session_id -> list of chat messages (same shape litelaw.py uses)
SESSIONS = {}


def get_session_messages(session_id):
    if session_id not in SESSIONS:
        SESSIONS[session_id] = [{"role": "system", "content": get_system_prompt()}]
    return SESSIONS[session_id]


def trim_context(session_messages):
    if len(session_messages) > MAX_CONTEXT_MESSAGES:
        system_prompt = session_messages[0]
        session_messages[:] = [system_prompt] + session_messages[-MAX_CONTEXT_MESSAGES:]


def web_run_agent(user_goal, session_messages):
    """
    Mirrors litelaw.run_agent()'s loop, but instead of printing to a terminal
    it collects each step as a structured event for the web UI to render.
    """
    steps = []
    session_messages.append({"role": "user", "content": f"Task: {user_goal}"})

    for step in range(MAX_STEPS):
        response = call_ollama(session_messages)
        if not response:
            steps.append({
                "type": "error",
                "text": "Could not connect to Ollama. Make sure it's running (ollama serve) and the model is pulled."
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
                "text": "Model returned an invalid step; nudging it back on format."
            })
            session_messages.append({
                "role": "user",
                "content": "Invalid layout. Return your move strictly using ACTION: RUN_COMMAND or ACTION: FINISHED."
            })
    else:
        steps.append({"type": "error", "text": "Reached maximum step limit for this task."})

    trim_context(session_messages)
    return steps


@app.route("/")
def index():
    return render_template_string(PAGE_HTML)


@app.route("/api/chat", methods=["POST"])
def chat():
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    session_id = session["sid"]

    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"steps": [{"type": "error", "text": "Empty message."}]})

    session_messages = get_session_messages(session_id)
    steps = web_run_agent(message, session_messages)
    return jsonify({"steps": steps})


@app.route("/api/clear", methods=["POST"])
def clear():
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    SESSIONS[session["sid"]] = [{"role": "system", "content": get_system_prompt()}]
    return jsonify({"ok": True})


PAGE_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>litelaw</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
@font-face {
  font-family: 'JetBrainsMono Nerd Font';
  src: url('https://cdn.jsdelivr.net/gh/ryanoasis/nerd-fonts@v3.2.1/patched-fonts/JetBrainsMono/Ligatures/Regular/JetBrainsMonoNerdFontMono-Regular.ttf') format('truetype');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'JetBrainsMono Nerd Font';
  src: url('https://cdn.jsdelivr.net/gh/ryanoasis/nerd-fonts@v3.2.1/patched-fonts/JetBrainsMono/Ligatures/Bold/JetBrainsMonoNerdFontMono-Bold.ttf') format('truetype');
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}

:root{
  --bg-0:#07040f;
  --bg-1:#0d0620;
  --bg-2:#160a33;
  --panel:#120a26cc;
  --panel-solid:#140b28;
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
  height:100%;
  margin:0;
  font-family: var(--mono);
  background: var(--bg-0);
  color: var(--text-0);
  overflow:hidden;
}

/* ---------- starfield backdrop ---------- */
#stars, #stars2, #stars3{
  position:fixed; inset:0; z-index:0; pointer-events:none;
}
.nebula{
  position:fixed; inset:0; z-index:0; pointer-events:none;
  background:
    radial-gradient(ellipse 900px 600px at 15% 15%, rgba(139,92,246,0.20), transparent 60%),
    radial-gradient(ellipse 800px 700px at 85% 25%, rgba(232,121,249,0.14), transparent 60%),
    radial-gradient(ellipse 900px 800px at 50% 100%, rgba(103,232,249,0.08), transparent 60%),
    linear-gradient(180deg, var(--bg-1) 0%, var(--bg-0) 55%, #050310 100%);
}

/* ---------- layout ---------- */
.app{
  position:relative; z-index:1;
  height:100vh;
  display:flex;
  flex-direction:column;
}

header{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:14px 22px;
  border-bottom:1px solid var(--border-soft);
  background: linear-gradient(180deg, rgba(20,11,40,0.85), rgba(20,11,40,0.55));
  backdrop-filter: blur(10px);
}

.brand{
  display:flex; align-items:center; gap:12px;
}
.brand-mark{
  width:36px; height:36px;
  border-radius:10px;
  display:flex; align-items:center; justify-content:center;
  background: radial-gradient(circle at 30% 30%, var(--violet-1), var(--violet-3) 70%);
  box-shadow: 0 0 18px rgba(139,92,246,0.65), inset 0 0 8px rgba(255,255,255,0.25);
  font-size:18px;
}
.brand-text h1{
  margin:0; font-size:17px; font-weight:800; letter-spacing:0.5px;
  background: linear-gradient(90deg, var(--violet-1), var(--magenta));
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
.brand-text span{
  display:block; margin-top:1px; font-size:11px; color:var(--text-dim); letter-spacing:0.4px;
}

.header-actions{ display:flex; align-items:center; gap:10px; }
.status-dot{
  width:8px; height:8px; border-radius:50%; background:var(--green);
  box-shadow:0 0 8px var(--green);
  display:inline-block;
}
.status-pill{
  display:flex; align-items:center; gap:6px;
  font-size:11px; color:var(--text-dim);
  border:1px solid var(--border-soft);
  padding:5px 10px; border-radius:999px;
  background:rgba(139,92,246,0.06);
}

button.ghost-btn{
  font-family:var(--mono);
  background:rgba(139,92,246,0.08);
  border:1px solid var(--border);
  color:var(--text-1);
  padding:7px 13px;
  border-radius:8px;
  font-size:12px;
  cursor:pointer;
  transition: all .15s ease;
}
button.ghost-btn:hover{
  background:rgba(139,92,246,0.18);
  border-color: var(--violet-1);
  color:#fff;
}

/* ---------- chat area ---------- */
main{
  flex:1;
  overflow-y:auto;
  padding: 26px 0 10px;
}
.chat-inner{
  max-width: 880px;
  margin:0 auto;
  padding: 0 22px 10px;
  display:flex;
  flex-direction:column;
  gap:16px;
}

.empty-state{
  margin-top:14vh;
  text-align:center;
  color:var(--text-dim);
}
.empty-state .glyph{
  font-size:40px;
  margin-bottom:10px;
  filter: drop-shadow(0 0 14px rgba(167,139,250,0.6));
}
.empty-state h2{
  color:var(--text-0);
  font-size:18px;
  margin:6px 0 4px;
}
.empty-state p{ font-size:12.5px; margin:0; }
.suggestions{
  display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-top:18px;
}
.chip{
  border:1px solid var(--border-soft);
  background:rgba(139,92,246,0.06);
  color:var(--text-1);
  padding:8px 12px;
  border-radius:10px;
  font-size:11.5px;
  cursor:pointer;
}
.chip:hover{ border-color:var(--violet-1); background:rgba(139,92,246,0.14); }

.row{ display:flex; width:100%; }
.row.user{ justify-content:flex-end; }
.row.assistant{ justify-content:flex-start; }

.bubble{
  max-width: 78%;
  padding: 11px 15px;
  border-radius: 14px;
  font-size: 13.5px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.bubble.user{
  background: linear-gradient(135deg, var(--violet-3), #5b21b6);
  color:#f5f3ff;
  border: 1px solid rgba(167,139,250,0.4);
  border-bottom-right-radius:4px;
  box-shadow: 0 4px 18px rgba(124,58,237,0.35);
}
.bubble.final{
  background: var(--panel-solid);
  border:1px solid var(--border-soft);
  border-bottom-left-radius:4px;
  color:var(--text-0);
}
.bubble.final::before{
  content:"⬡ litelaw";
  display:block;
  font-size:10.5px;
  letter-spacing:0.6px;
  color:var(--violet-1);
  margin-bottom:6px;
  font-weight:700;
}

.thought{
  max-width:78%;
  font-size:12px;
  color:var(--text-dim);
  font-style:italic;
  padding:2px 4px 2px 2px;
}
.thought::before{ content:"✧ "; color:var(--violet-1); font-style:normal; }

.term-block{
  max-width:78%;
  border-radius:10px;
  overflow:hidden;
  border:1px solid var(--border-soft);
  background: #0b0618;
  box-shadow: inset 0 0 0 1px rgba(139,92,246,0.06);
}
.term-head{
  display:flex; align-items:center; gap:8px;
  padding:7px 12px;
  background: rgba(139,92,246,0.08);
  border-bottom:1px solid var(--border-soft);
  font-size:10.5px;
  color: var(--text-dim);
  letter-spacing:0.4px;
}
.term-dots{ display:flex; gap:5px; }
.term-dots span{ width:8px; height:8px; border-radius:50%; display:inline-block; }
.term-dots span:nth-child(1){ background:#ff5f56; }
.term-dots span:nth-child(2){ background:#ffbd2e; }
.term-dots span:nth-child(3){ background:#27c93f; }
.term-body{
  padding:11px 13px;
  font-size:12.5px;
  line-height:1.6;
  white-space:pre-wrap;
  word-wrap:break-word;
}
.term-body.command{ color: var(--cyan); }
.term-body.command::before{ content:"$ "; color: var(--violet-1); }
.term-body.output{ color: var(--text-1); }

.warning-line, .error-line{
  max-width:78%;
  font-size:11.5px;
  padding:7px 11px;
  border-radius:8px;
  border:1px solid;
}
.warning-line{ color:var(--yellow); border-color:rgba(250,204,21,0.35); background:rgba(250,204,21,0.06); }
.error-line{ color:var(--red); border-color:rgba(248,113,113,0.35); background:rgba(248,113,113,0.07); }

.thinking-row{
  display:flex; align-items:center; gap:8px;
  color:var(--text-dim); font-size:12px; padding:2px 4px;
}
.thinking-dots span{
  display:inline-block; width:5px; height:5px; margin-right:3px;
  border-radius:50%; background:var(--violet-1);
  animation: blink 1.2s infinite ease-in-out;
}
.thinking-dots span:nth-child(2){ animation-delay:.2s; }
.thinking-dots span:nth-child(3){ animation-delay:.4s; }
@keyframes blink{ 0%,80%,100%{ opacity:.25; } 40%{ opacity:1; } }

/* ---------- input ---------- */
.input-wrap{
  border-top:1px solid var(--border-soft);
  background: linear-gradient(0deg, rgba(20,11,40,0.9), rgba(20,11,40,0.5));
  backdrop-filter: blur(10px);
  padding: 14px 22px 18px;
}
.input-inner{
  max-width:880px; margin:0 auto;
  display:flex; align-items:flex-end; gap:10px;
  background: rgba(139,92,246,0.06);
  border:1px solid var(--border);
  border-radius:14px;
  padding:10px 10px 10px 16px;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.input-inner:focus-within{
  border-color: var(--violet-1);
  box-shadow: 0 0 0 3px rgba(167,139,250,0.15);
}
textarea#msg{
  flex:1;
  resize:none;
  background:transparent;
  border:none;
  outline:none;
  color: var(--text-0);
  font-family: var(--mono);
  font-size:13.5px;
  line-height:1.5;
  max-height:160px;
  padding:6px 0;
}
textarea#msg::placeholder{ color: var(--text-dim); }

.send-btn{
  width:38px; height:38px;
  border-radius:10px;
  border:none;
  cursor:pointer;
  display:flex; align-items:center; justify-content:center;
  background: linear-gradient(135deg, var(--violet-1), var(--violet-3));
  color:white;
  font-size:15px;
  box-shadow: 0 2px 12px rgba(124,58,237,0.5);
  transition: transform .12s ease;
  flex-shrink:0;
}
.send-btn:hover{ transform: translateY(-1px); }
.send-btn:disabled{ opacity:.4; cursor:not-allowed; transform:none; }

.foot-note{
  max-width:880px; margin:8px auto 0;
  text-align:center;
  font-size:10.5px;
  color: var(--text-dim);
  opacity:.75;
}

::-webkit-scrollbar{ width:9px; }
::-webkit-scrollbar-track{ background:transparent; }
::-webkit-scrollbar-thumb{ background: var(--border); border-radius:8px; }
::-webkit-scrollbar-thumb:hover{ background: var(--violet-3); }
</style>
</head>
<body>

<div class="nebula"></div>
<canvas id="stars"></canvas>

<div class="app">
  <header>
    <div class="brand">
      <div class="brand-mark">⬡</div>
      <div class="brand-text">
        <h1>litelaw</h1>
        <span>local automation agent</span>
      </div>
    </div>
    <div class="header-actions">
      <div class="status-pill"><span class="status-dot"></span> auto-approve on</div>
      <button class="ghost-btn" id="clearBtn">✦ clear session</button>
    </div>
  </header>

  <main id="main">
    <div class="chat-inner" id="chatInner">
      <div class="empty-state" id="emptyState">
        <div class="glyph">⬡</div>
        <h2>What should litelaw run?</h2>
        <p>Ask in plain language — it'll plan and execute terminal commands on this machine.</p>
        <div class="suggestions">
          <div class="chip" data-msg="list all .pdf files in my Downloads folder">list .pdf files in Downloads</div>
          <div class="chip" data-msg="create a folder called notes and a file inside it called todo.txt with the text 'buy milk'">create a folder + file with text</div>
          <div class="chip" data-msg="show me git status for the current directory">git status</div>
          <div class="chip" data-msg="check disk usage and free memory">disk + memory usage</div>
        </div>
      </div>
    </div>
  </main>

  <div class="input-wrap">
    <div class="input-inner">
      <textarea id="msg" rows="1" placeholder="Message litelaw..."></textarea>
      <button class="send-btn" id="sendBtn">➤</button>
    </div>
    <div class="foot-note">litelaw runs real shell commands on this machine with auto-approve enabled. Review requests carefully.</div>
  </div>
</div>

<script>
// ---------- starfield ----------
const canvas = document.getElementById('stars');
const ctx = canvas.getContext('2d');
let stars = [];
function resizeCanvas(){
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  stars = [];
  const count = Math.floor((canvas.width * canvas.height) / 9000);
  for(let i=0;i<count;i++){
    stars.push({
      x: Math.random()*canvas.width,
      y: Math.random()*canvas.height,
      r: Math.random()*1.3 + 0.2,
      a: Math.random(),
      d: (Math.random()*0.015)+0.003
    });
  }
}
function drawStars(){
  ctx.clearRect(0,0,canvas.width,canvas.height);
  for(const s of stars){
    s.a += s.d;
    if(s.a > 1 || s.a < 0) s.d *= -1;
    ctx.beginPath();
    ctx.fillStyle = `rgba(196,181,253,${Math.abs(Math.sin(s.a))})`;
    ctx.arc(s.x, s.y, s.r, 0, Math.PI*2);
    ctx.fill();
  }
  requestAnimationFrame(drawStars);
}
window.addEventListener('resize', resizeCanvas);
resizeCanvas();
drawStars();

// ---------- chat logic ----------
const chatInner = document.getElementById('chatInner');
const emptyState = document.getElementById('emptyState');
const msgEl = document.getElementById('msg');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const mainEl = document.getElementById('main');

function scrollBottom(){
  mainEl.scrollTop = mainEl.scrollHeight;
}

function hideEmptyState(){
  if(emptyState) emptyState.style.display = 'none';
}

function addUserBubble(text){
  hideEmptyState();
  const row = document.createElement('div');
  row.className = 'row user';
  row.innerHTML = `<div class="bubble user"></div>`;
  row.querySelector('.bubble').textContent = text;
  chatInner.appendChild(row);
  scrollBottom();
}

function addThinkingRow(){
  const row = document.createElement('div');
  row.className = 'row assistant';
  row.id = 'thinkingRow';
  row.innerHTML = `<div class="thinking-row">🤖 thinking
    <span class="thinking-dots"><span></span><span></span><span></span></span>
  </div>`;
  chatInner.appendChild(row);
  scrollBottom();
}

function removeThinkingRow(){
  const el = document.getElementById('thinkingRow');
  if(el) el.remove();
}

function addStepNode(step){
  const row = document.createElement('div');
  row.className = 'row assistant';

  if(step.type === 'thought'){
    row.innerHTML = `<div class="thought"></div>`;
    row.querySelector('.thought').textContent = step.text;
  } else if(step.type === 'command'){
    row.innerHTML = `
      <div class="term-block">
        <div class="term-head"><span class="term-dots"><span></span><span></span><span></span></span> command</div>
        <div class="term-body command"></div>
      </div>`;
    row.querySelector('.term-body').textContent = step.text;
  } else if(step.type === 'output'){
    row.innerHTML = `
      <div class="term-block">
        <div class="term-head"><span class="term-dots"><span></span><span></span><span></span></span> output</div>
        <div class="term-body output"></div>
      </div>`;
    row.querySelector('.term-body').textContent = step.text || '(no output)';
  } else if(step.type === 'final'){
    row.innerHTML = `<div class="bubble final"></div>`;
    row.querySelector('.bubble').textContent = step.text;
  } else if(step.type === 'warning'){
    row.innerHTML = `<div class="warning-line"></div>`;
    row.querySelector('.warning-line').textContent = '⚠ ' + step.text;
  } else if(step.type === 'error'){
    row.innerHTML = `<div class="error-line"></div>`;
    row.querySelector('.error-line').textContent = '✕ ' + step.text;
  }
  chatInner.appendChild(row);
  scrollBottom();
}

async function sendMessage(){
  const text = msgEl.value.trim();
  if(!text) return;
  msgEl.value = '';
  msgEl.style.height = 'auto';
  sendBtn.disabled = true;

  addUserBubble(text);
  addThinkingRow();

  try{
    const res = await fetch('/api/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message: text})
    });
    const data = await res.json();
    removeThinkingRow();
    for(const step of (data.steps || [])){
      addStepNode(step);
      await new Promise(r => setTimeout(r, 120));
    }
  }catch(e){
    removeThinkingRow();
    addStepNode({type:'error', text: 'Could not reach litelaw backend: ' + e});
  }finally{
    sendBtn.disabled = false;
    msgEl.focus();
  }
}

sendBtn.addEventListener('click', sendMessage);
msgEl.addEventListener('keydown', (e) => {
  if(e.key === 'Enter' && !e.shiftKey){
    e.preventDefault();
    sendMessage();
  }
});
msgEl.addEventListener('input', () => {
  msgEl.style.height = 'auto';
  msgEl.style.height = Math.min(msgEl.scrollHeight, 160) + 'px';
});

document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => {
    msgEl.value = chip.getAttribute('data-msg');
    sendMessage();
  });
});

clearBtn.addEventListener('click', async () => {
  await fetch('/api/clear', {method:'POST'});
  chatInner.innerHTML = '';
  chatInner.appendChild(emptyState);
  emptyState.style.display = 'block';
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("====================================================")
    print(" ⬡  litelaw web UI starting")
    print(" Open: http://localhost:5000")
    print("====================================================")
    app.run(host="0.0.0.0", port=5000, debug=False)
