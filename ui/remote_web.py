PAGE_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#FF6B00">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>Agently</title>
<link rel="icon" href="/icon.png">
<style>
  :root { --bg:#0d0d0f; --card:#17171b; --line:#26262c; --fg:#f2f2f4;
          --mut:#8e8e99; --acc:#FF6B00; }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  html,body { margin:0; height:100%; background:var(--bg); color:var(--fg);
    font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  body { display:flex; flex-direction:column; height:100dvh; }

  header { display:flex; align-items:center; gap:10px; padding:12px 14px;
    padding-top:calc(12px + env(safe-area-inset-top));
    border-bottom:1px solid var(--line); background:var(--bg); }
  .dot { width:9px; height:9px; border-radius:50%; background:var(--mut); flex:0 0 auto; }
  .dot.on { background:#2ecc71; } .dot.off { background:#e74c3c; }
  header h1 { font-size:16px; margin:0; font-weight:600; letter-spacing:.2px; }
  header .sp { flex:1; }
  .lbl { font-size:12px; color:var(--mut); }

  #log { flex:1; overflow-y:auto; padding:14px; display:flex; flex-direction:column; gap:10px; }

  .msg { max-width:82%; padding:10px 13px; border-radius:16px; white-space:pre-wrap;
         word-break:break-word; }
  .u { align-self:flex-end; background:var(--acc); color:#14100c; font-weight:500;
       border-bottom-right-radius:5px; }
  .b { align-self:flex-start; background:var(--card); border:1px solid var(--line);
       border-bottom-left-radius:5px; }
  .sys { align-self:center; color:var(--mut); font-size:13px; background:none; }
  .busy { align-self:center; color:var(--mut); font-size:13px; }

  #bar { padding:10px 14px calc(10px + env(safe-area-inset-bottom));
         border-top:1px solid var(--line); background:var(--bg); }

  #ask { display:none; background:var(--card); border:1px solid var(--acc);
         border-radius:14px; padding:12px; margin-bottom:10px; }
  #ask .t { font-size:13px; color:var(--mut); margin-bottom:4px; }
  #ask .d { margin-bottom:11px; font-weight:500; }
  #ask .row { display:flex; gap:9px; }
  #ask button { flex:1; padding:12px; font-size:15px; font-weight:600; border-radius:11px;
                border:none; }
  #yes { background:var(--acc); color:#14100c; }
  #no  { background:#26262c; color:var(--fg); }

  .inrow { display:flex; gap:9px; align-items:flex-end; }
  input[type=text] { flex:1; padding:12px 14px; border-radius:22px; border:1px solid var(--line);
    background:var(--card); color:var(--fg); font-size:16px; outline:none; }
  input[type=text]:focus { border-color:var(--acc); }
  button.icon { width:48px; height:48px; flex:0 0 48px; border-radius:50%; border:none;
    background:var(--card); color:var(--fg); font-size:20px; display:grid; place-items:center; }
  button.icon.rec { background:var(--acc); color:#14100c; animation:pulse 1.1s infinite; }
  button.icon:disabled { opacity:.4; }
  @keyframes pulse { 50% { transform:scale(1.08); } }

  #shot { display:none; padding:0 14px 10px; }
  #shot img { width:100%; border-radius:12px; border:1px solid var(--line); display:block; }

  #gate { position:fixed; inset:0; background:var(--bg); display:grid; place-items:center;
          padding:24px; z-index:9; }
  #gate .card { width:100%; max-width:340px; background:var(--card); border:1px solid var(--line);
                border-radius:16px; padding:22px; }
  #gate h2 { margin:0 0 6px; font-size:18px; }
  #gate p { color:var(--mut); font-size:13px; margin:0 0 16px; }
  #gate input { width:100%; padding:12px; border-radius:10px; border:1px solid var(--line);
                background:var(--bg); color:var(--fg); font-size:16px; outline:none; }
  #gate button { width:100%; margin-top:12px; padding:13px; border:none; border-radius:11px;
                 background:var(--acc); color:#14100c; font-weight:600; font-size:15px; }
  #gate .err { color:#e74c3c; font-size:13px; margin-top:10px; min-height:18px; }
</style>
</head>
<body>

<div id="gate"><div class="card">
  <h2>Connect to Agently</h2>
  <p>Paste the access token shown in the Agently app on your PC.</p>
  <input id="tok" type="text" placeholder="Access token" autocomplete="off">
  <button id="go">Connect</button>
  <div class="err" id="gerr"></div>
</div></div>

<header>
  <div class="dot" id="dot"></div>
  <h1>Agently</h1>
  <div class="sp"></div>
  <span class="lbl" id="stat"></span>
</header>

<div id="log"><div class="sys">Say something or type below.</div></div>
<div id="shot"><img id="shotimg" alt="screen"></div>

<div id="bar">
  <div id="ask">
    <div class="t">Confirm on your phone</div>
    <div class="d" id="askd"></div>
    <div class="row"><button id="no">Cancel</button><button id="yes">Yes, do it</button></div>
  </div>
  <div class="inrow">
    <button class="icon" id="mic">&#9679;</button>
    <input id="txt" type="text" placeholder="Ask anything..." autocomplete="off">
    <button class="icon" id="cam">&#128247;</button>
  </div>
</div>

<script>
(function () {
  var TOKEN = window.__AGENTLY_TOKEN__ || localStorage.getItem("agently_token") || "";
  // Fallback: a scanned QR link may carry ?t=<token> to log straight in.
  (function () {
    var m = /[?&]t=([^&]+)/.exec(location.search);
    if (m) {
      try { TOKEN = decodeURIComponent(m[1]); } catch (e) {}
      history.replaceState(null, "", location.pathname);
    }
    if (TOKEN) { try { localStorage.setItem("agently_token", TOKEN); } catch (e) {} }
  })();
  var logEl = document.getElementById("log"), askEl = document.getElementById("ask");
  var askd = document.getElementById("askd"), statEl = document.getElementById("stat");
  var dotEl = document.getElementById("dot"), shotEl = document.getElementById("shot");
  var micEl = document.getElementById("mic"), txtEl = document.getElementById("txt");
  var busy = false, pendingId = null, rec = null, chunks = [];

  if (TOKEN) { document.getElementById("gate").style.display = "none"; boot(); }
  else document.getElementById("tok").focus();

  document.getElementById("go").onclick = function () {
    var t = document.getElementById("tok").value.trim();
    if (!t) return;
    localStorage.setItem("agently_token", t); TOKEN = t;
    document.getElementById("gerr").textContent = "";
    document.getElementById("gate").style.display = "none";
    boot();
  };

  function add(cls, text) {
    var d = document.createElement("div"); d.className = "msg " + cls;
    d.textContent = text; logEl.appendChild(d); logEl.scrollTop = logEl.scrollHeight;
    return d;
  }

  function api(path, body) {
    return fetch(path, {
      method: body ? "POST" : "GET",
      headers: { "Content-Type": "application/json", "X-Agently-Token": TOKEN },
      body: body ? JSON.stringify(body) : undefined
    }).then(function (r) {
      if (r.status === 401) throw new Error("bad token");
      return r.json();
    });
  }

  function boot() {
    setInterval(poll, 4000); poll();
  }

  function poll() {
    api("/api/status").then(function (s) {
      dotEl.className = "dot on";
      statEl.textContent = s.timers ? (s.timers + " timer" + (s.timers > 1 ? "s" : "")) : "online";
    }).catch(function (e) {
      dotEl.className = "dot off";
      statEl.textContent = e.message === "bad token" ? "bad token" : "offline";
    });
  }

  function send(text) {
    if (busy || !text.trim()) return;
    busy = true; add("u", text);
    var b = add("busy", "Thinking...");
    api("/api/command", { text: text }).then(function (r) {
      b.remove(); handle(r);
    }).catch(function (e) {
      b.remove(); add("sys", e.message === "bad token" ? "Bad token." : "Connection lost.");
    }).then(function () { busy = false; });
  }

  function handle(r) {
    if (r.type === "confirm") {
      pendingId = r.confirm_id; askd.textContent = r.desc; askEl.style.display = "block";
    } else if (r.type === "reply") {
      add("b", r.reply || "Done.");
    } else if (r.type === "shot") {
      document.getElementById("shotimg").src = "data:image/jpeg;base64," + r.image;
      shotEl.style.display = "block";
      add("b", r.text || "");
    }
  }

  txtEl.addEventListener("keydown", function (e) { if (e.key === "Enter") send(txtEl.value), txtEl.value = ""; });

  # ---- mic ----
  micEl.onclick = function () {
    if (rec) { rec.stop(); return; }
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      rec = new MediaRecorder(stream); chunks = [];
      rec.ondataavailable = function (e) { chunks.push(e.data); };
      rec.onstop = function () {
        stream.getTracks().forEach(function (t) { t.stop(); });
        micEl.classList.remove("rec"); micEl.textContent = "\u25CF"; rec = null;
        var blob = new Blob(chunks, { type: chunks[0] ? chunks[0].type : "audio/webm" });
        var fr = new FileReader();
        fr.onload = function () {
          var b64 = String(fr.result).split(",")[1];
          add("u", "\uD83C\uDFA4 voice message");
          var b = add("busy", "Listening...");
          api("/api/voice", { audio: b64 }).then(function (r) {
            b.remove();
            if (r.type === "error") add("sys", r.reply || "I didn't catch that.");
            else {
              add("u", r.transcript || "(voice)");
              handle(r);
            }
          }).catch(function () { b.remove(); add("sys", "Connection lost."); });
        };
        fr.readAsDataURL(blob);
      };
      rec.start(); micEl.classList.add("rec"); micEl.textContent = "\u25A0";
    }).catch(function () { add("sys", "Microphone blocked - allow access."); });
  };

  // ---- screenshot ----
  document.getElementById("cam").onclick = function () {
    var b = add("busy", "Grabbing screen...");
    api("/api/screenshot").then(function (r) { b.remove(); handle(r); })
      .catch(function () { b.remove(); add("sys", "Connection lost."); });
  };

  // ---- confirm ----
  function resolve(ok) {
    if (!pendingId) return;
    var id = pendingId; pendingId = null; askEl.style.display = "none";
    var b = add("busy", ok ? "Working..." : "");
    api("/api/confirm", { confirm_id: id, approve: ok }).then(function (r) {
      b.remove(); handle(r);
    }).catch(function () { b.remove(); add("sys", "Connection lost."); });
  }
  document.getElementById("yes").onclick = function () { resolve(true); };
  document.getElementById("no").onclick = function () { resolve(false); };
})();
</script>
</body>
</html>"""