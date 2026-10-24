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
  :root {
    --bg:#09090b; --panel:#18181b; --card:#1e1e22; --line:#27272a;
    --fg:#fafafa; --mut:#a1a1aa; --mut2:#71717a;
    --acc:#FF6B00; --acc-light:#FF8533; --acc-dark:#E05E00;
    --ok:#22c55e; --warn:#f59e0b; --err:#ef4444;
  }
  * { box-sizing:border-box; -webkit-tap-highlight-color:transparent; margin:0; padding:0; }
  html,body { height:100%; background:var(--bg); color:var(--fg);
    font:15px/1.5 "SF Pro Display","SF Pro Text","Segoe UI Variable","Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    -webkit-font-smoothing:antialiased; }
  body { display:flex; flex-direction:column; height:100dvh; overflow:hidden; }

  /* ---------- header ---------- */
  header { display:flex; align-items:center; gap:10px; padding:12px 16px;
    padding-top:calc(12px + env(safe-area-inset-top));
    border-bottom:1px solid var(--line); background:var(--panel); flex:0 0 auto; }
  .dot { width:8px; height:8px; border-radius:50%; background:var(--mut2); flex:0 0 auto; }
  .dot.on { background:var(--ok); } .dot.off { background:var(--err); }
  header h1 { font-size:17px; margin:0; font-weight:700; letter-spacing:-0.3px; }
  header .sp { flex:1; }
  .lbl { font-size:12px; color:var(--mut); font-weight:500; }

  /* ---------- chat log ---------- */
  #log { flex:1; overflow-y:auto; padding:14px 16px; display:flex; flex-direction:column;
    gap:8px; scroll-behavior:smooth; }
  .msg { max-width:84%; padding:10px 14px; border-radius:14px; white-space:pre-wrap;
    word-break:break-word; line-height:1.45; font-size:14.5px; }
  .u { align-self:flex-end; background:var(--acc); color:#09090b; font-weight:500;
       border-bottom-right-radius:4px; }
  .b { align-self:flex-start; background:var(--card); border:1px solid var(--line);
       border-bottom-left-radius:4px; }
  .sys { align-self:center; color:var(--mut); font-size:12.5px; background:none; padding:4px 0; }
  .busy { align-self:center; color:var(--mut); font-size:12.5px; }

  /* ---------- confirm bar ---------- */
  #ask { display:none; margin:0 16px 8px; background:var(--card); border:1px solid var(--acc);
    border-radius:14px; padding:14px; }
  #ask .t { font-size:12px; color:var(--mut); margin-bottom:3px; font-weight:500; }
  #ask .d { margin-bottom:12px; font-weight:600; font-size:14px; }
  #ask .row { display:flex; gap:8px; }
  #ask button { flex:1; padding:11px; font-size:14px; font-weight:600; border-radius:10px;
                border:none; cursor:pointer; }
  #yes { background:var(--acc); color:#09090b; }
  #yes:active { background:var(--acc-dark); }
  #no { background:var(--line); color:var(--fg); }
  #no:active { background:#3f3f46; }

  /* ---------- bottom bar ---------- */
  #bar { padding:10px 14px calc(10px + env(safe-area-inset-bottom));
    border-top:1px solid var(--line); background:var(--panel); flex:0 0 auto; }

  .inrow { display:flex; gap:8px; align-items:center; }
  input[type=text] { flex:1 1 auto; min-width:0; padding:11px 15px; border-radius:20px;
    border:1px solid var(--line); background:var(--card); color:var(--fg);
    font-size:15px; outline:none; transition:border-color .15s; }
  input[type=text]:focus { border-color:var(--acc); }
  input[type=text]::placeholder { color:var(--mut2); }

  .ico { flex:0 0 40px; width:40px; height:40px; border-radius:50%;
    border:1px solid var(--line); background:var(--card); color:var(--mut);
    display:grid; place-items:center; padding:0; cursor:pointer;
    transition:all .15s; }
  .ico svg { width:18px; height:18px; display:block; }
  .ico:active { background:#27272a; }
  .ico.on { background:var(--acc); border-color:var(--acc); color:#09090b; }

  #talk { flex:0 0 42px; width:42px; height:42px; border-radius:50%; border:none;
    background:var(--acc); color:#09090b; display:grid; place-items:center;
    padding:0; cursor:pointer; box-shadow:0 2px 10px rgba(255,107,0,.28);
    transition:transform .1s, background .2s; }
  #talk svg { width:19px; height:19px; display:block; }
  #talk:active { transform:scale(.93); }
  #talk.rec { background:var(--err); animation:recpulse 1.1s infinite; }
  @keyframes recpulse {
    0%,100% { box-shadow:0 0 0 0 rgba(255,59,48,.5); }
    50%     { box-shadow:0 0 0 10px rgba(255,59,48,0); }
  }

  /* ---- screenshots ride along in the chat ---- */
  .shotwrap { align-self:flex-start; max-width:88%; padding:5px; border-radius:14px;
    background:var(--card); border:1px solid var(--line); border-bottom-left-radius:4px;
    cursor:pointer; }
  .shotwrap img { display:block; width:100%; border-radius:9px; }
  .shotwrap .cap { font-size:10.5px; color:var(--mut); padding:4px 2px 1px; }

  /* ---- live screen view ---- */
  #live { display:none; padding:0 14px 10px; }
  #live img { width:100%; aspect-ratio:16/9; object-fit:contain; border-radius:12px;
    border:1px solid var(--line); display:block; background:#000; min-height:120px; }
  .livebar { display:flex; align-items:center; gap:8px; margin-bottom:6px;
    font-size:11px; color:var(--mut); font-weight:600; }
  .livebar .rd { width:8px; height:8px; border-radius:50%; background:#FF3B30;
    animation:blink 1s infinite; }
  @keyframes blink { 50% { opacity:.25; } }
  .livebar .sp { flex:1; }
  .mini { flex:0 0 30px; width:30px; height:30px; border-radius:8px; padding:0;
    border:1px solid var(--line); background:var(--card); color:var(--mut);
    display:grid; place-items:center; cursor:pointer; }
  .mini svg { width:15px; height:15px; display:block; }
  .mini.on { color:var(--acc); border-color:var(--acc); }
  .mini:active { background:#27272a; }

  #live.fs { position:fixed; inset:0; z-index:20; background:#000;
    display:flex; flex-direction:column; justify-content:center; }
  #live.fs .livebar { position:absolute; top:calc(8px + env(safe-area-inset-top));
    left:12px; right:12px; }
  #live.fs img { border:0; border-radius:0; width:100%; height:100%;
    object-fit:contain; }

  /* ---- mic warning ---- */
  #micwarn { display:none; margin:0 14px 10px; padding:11px 13px; border-radius:12px;
    background:#2a1a10; border:1px solid var(--acc); color:#ffd9bd; font-size:12.5px;
    line-height:1.45; }

  /* ---------- gate ---------- */
  #gate { position:fixed; inset:0; background:var(--bg); display:grid; place-items:center;
          padding:24px; z-index:9; }
  #gate .card { width:100%; max-width:360px; background:var(--card); border:1px solid var(--line);
                border-radius:16px; padding:26px; }
  #gate h2 { margin:0 0 6px; font-size:20px; font-weight:700; letter-spacing:-0.3px; }
  #gate p { color:var(--mut); font-size:13px; margin:0 0 16px; line-height:1.45; }
  #gate input { width:100%; padding:12px; border-radius:10px; border:1px solid var(--line);
                background:var(--bg); color:var(--fg); font-size:16px; outline:none;
                transition:border-color .15s; }
  #gate input:focus { border-color:var(--acc); }
  #gate button { width:100%; margin-top:12px; padding:13px; border:none; border-radius:11px;
                 background:var(--acc); color:#09090b; font-weight:600; font-size:15px;
                 cursor:pointer; transition:background .15s; }
  #gate button:active { background:var(--acc-dark); }
  #gate .err { color:var(--err); font-size:13px; margin-top:10px; min-height:18px; }
</style>
</head>
<body>

<div id="gate"><div class="card">
  <h2>Connect to Agently</h2>
  <p id="gatehint">Open this page by <b>scanning the QR code</b> in the
  &ldquo;Remote&rdquo; section of Agently on your PC &mdash; it signs you in
  automatically. Paste the token only if the camera can't read the QR.</p>
  <input id="tok" type="text" placeholder="Access token (fallback)" autocomplete="off">
  <button id="go">Connect</button>
  <div class="err" id="gerr"></div>
</div></div>

<header>
  <div class="dot" id="dot"></div>
  <h1>Agently</h1>
  <div class="sp"></div>
  <span class="lbl" id="stat"></span>
</header>

<div id="log"><div class="sys">Tap the mic to talk, or type a message.</div></div>

<div id="live">
  <div class="livebar">
    <span class="rd"></span> LIVE SCREEN <span id="livenote"></span>
    <span class="sp"></span>
    <button class="mini" id="sndbtn" aria-label="Sound">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
        <line id="sndx" x1="17" y1="9" x2="23" y2="15"></line>
        <line id="sndx2" x1="23" y1="9" x2="17" y2="15"></line>
      </svg>
    </button>
    <button class="mini" id="fsbtn" aria-label="Fullscreen">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round">
        <polyline points="4 9 4 4 9 4"></polyline>
        <polyline points="15 4 20 4 20 9"></polyline>
        <polyline points="20 15 20 20 15 20"></polyline>
        <polyline points="9 20 4 20 4 15"></polyline>
      </svg>
    </button>
  </div>
  <img id="liveimg" alt="live screen">
</div>

<div id="micwarn" class="warn">
  <b>Microphone needs a secure (https) address.</b><br>
  Browsers block the mic on plain http. Run <b>Set up HTTPS</b> in the Agently
  app on your PC, then open the https link it gives you.
</div>

<div id="bar">
  <div id="ask">
    <div class="t">Confirm on your phone</div>
    <div class="d" id="askd"></div>
    <div class="row"><button id="no">Cancel</button><button id="yes">Yes, do it</button></div>
  </div>
  <div class="inrow">
    <button id="talk" aria-label="Talk"><svg viewBox="0 0 24 24" fill="none"
      stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3"></rect>
      <path d="M5 11a7 7 0 0 0 14 0"></path>
      <line x1="12" y1="18" x2="12" y2="22"></line>
    </svg></button>
    <input id="txt" type="text" placeholder="Message Agently..." autocomplete="off">
    <button class="ico" id="livebtn" aria-label="Watch my screen"><svg viewBox="0 0 24 24"
      fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="3.5" width="20" height="13" rx="2"></rect>
      <line x1="8" y1="21" x2="16" y2="21"></line>
      <line x1="12" y1="16.5" x2="12" y2="21"></line>
    </svg></button>
    <button class="ico" id="cam" aria-label="Take a screenshot"><svg viewBox="0 0 24 24"
      fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M3 8.5A2 2 0 0 1 5 6.5h1.5l1-2h4l1 2H17a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
      <circle cx="11" cy="12.5" r="3.2"></circle>
    </svg></button>
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
  var dotEl = document.getElementById("dot");
  var txtEl = document.getElementById("txt");
  var busy = false, pendingId = null, rec = null, chunks = [];
  var talkEl = document.getElementById("talk");
  var liveEl = document.getElementById("live"), liveImg = document.getElementById("liveimg");
  var liveBtn = document.getElementById("livebtn"), liveOn = false;

  if (TOKEN) { document.getElementById("gate").style.display = "none"; boot(); }
  else document.getElementById("tok").focus();

  window.addEventListener("error", function (ev) {
    var g = document.getElementById("gerr");
    if (g && document.getElementById("gate").style.display !== "none") {
      g.textContent = "Page error: " + (ev.message || "unknown");
    }
  });

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
      if (e.message === "bad token") {
        // Stale/wrong saved token - forget it and ask again.
        try { localStorage.removeItem("agently_token"); } catch (x) {}
        TOKEN = "";
        document.getElementById("gate").style.display = "grid";
        document.getElementById("gerr").textContent =
          "That token was rejected. Scan the QR again, or paste a new token.";
        statEl.textContent = "sign in again";
        return;
      }
      statEl.textContent = "offline";
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

  function addShot(dataUrl, caption) {
    // only ever one screenshot in the chat, and it scrolls like a message
    var old = logEl.querySelector(".shotwrap");
    if (old) old.remove();
    var wrap = document.createElement("div");
    wrap.className = "shotwrap";
    var img = document.createElement("img");
    img.src = dataUrl;
    img.alt = "screen capture";
    wrap.appendChild(img);
    var cap = document.createElement("div");
    cap.className = "cap";
    cap.textContent = (caption || "Screenshot") + " — tap to remove";
    wrap.appendChild(cap);
    wrap.addEventListener("click", function () { wrap.remove(); });
    logEl.appendChild(wrap);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function handle(r) {
    if (r.type === "confirm") {
      pendingId = r.confirm_id; askd.textContent = r.desc; askEl.style.display = "block";
    } else if (r.type === "reply") {
      add("b", r.reply || "Done.");
    } else if (r.type === "shot") {
      addShot("data:image/jpeg;base64," + r.image, r.text);
    }
  }

  txtEl.addEventListener("keydown", function (e) { if (e.key === "Enter") send(txtEl.value), txtEl.value = ""; });

  // ---- big TALK button (mic asked once, then never again) ----
  var warmStream = null;
  var MIC_SVG = talkEl.innerHTML;   // keep the mic glyph so we can restore it
  var secure = (window.isSecureContext !== false);

  function micWarn(show) {
    var w = document.getElementById("micwarn");
    if (w) w.style.display = show ? "block" : "none";
  }
  if (!secure) micWarn(true);

  function micGrantedFlag() {
    try { return localStorage.getItem("agently_mic_ok") === "1"; } catch (e) { return false; }
  }
  function markMicGranted() {
    try { localStorage.setItem("agently_mic_ok", "1"); } catch (e) {}
  }

  // Open the mic stream exactly once and keep it warm, so the browser's
  // permission prompt appears only the first time and never again.
  function openMic() {
    if (warmStream) return Promise.resolve(warmStream);
    if (!secure) {
      return Promise.reject(new Error("insecure"));
    }
    return navigator.mediaDevices.getUserMedia({ audio: true }).then(function (s) {
      warmStream = s;
      markMicGranted();
      return s;
    });
  }

  // If permission was already given earlier, silently keep the mic warm so the
  // first tap is instant. Never triggers a prompt.
  function warmMicIfAllowed() {
    if (!navigator.permissions || !navigator.permissions.query) return;
    navigator.permissions.query({ name: "microphone" }).then(function (p) {
      if (p.state === "granted" && micGrantedFlag()) {
        openMic().catch(function () {});
      }
    }).catch(function () {});
  }

  talkEl.onclick = function () {
    if (rec) { rec.stop(); return; }
    openMic().then(function (stream) {
      rec = new MediaRecorder(stream); chunks = [];
      rec.ondataavailable = function (e) { chunks.push(e.data); };
      rec.onstop = function () {
        talkEl.classList.remove("rec");
        talkEl.innerHTML = MIC_SVG;
        rec = null;
        var blob = new Blob(chunks, { type: chunks[0] ? chunks[0].type : "audio/webm" });
        if (!blob.size) { add("sys", "Nothing recorded."); return; }
        var fr = new FileReader();
        fr.onload = function () {
          var b64 = String(fr.result).split(",")[1];
          add("u", "\uD83C\uDFA4 voice message");
          var b = add("busy", "Listening...");
          api("/api/voice", { audio: b64 }).then(function (r) {
            b.remove();
            if (r.type === "error") add("sys", r.reply || "I didn't catch that.");
            else { add("u", r.transcript || "(voice)"); handle(r); }
          }).catch(function () { b.remove(); add("sys", "Connection lost."); });
        };
        fr.readAsDataURL(blob);
      };
      rec.start();
      talkEl.classList.add("rec");
      talkEl.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor" ' +
        'stroke="none"><rect x="6" y="6" width="12" height="12" rx="2"></rect></svg>';
      statEl.textContent = "listening…";
      statEl.style.color = "#FF3B30";
    }).catch(function (e) {
      if (e && e.message === "insecure") {
        add("sys", "Microphone is blocked because this page is not https. "
          + "Use the https link from Agently (Set up HTTPS).");
        micWarn(true);
      } else {
        add("sys", micGrantedFlag()
          ? "Microphone is blocked for this site - re-allow it in your browser settings."
          : "Allow microphone access once - Agently will remember and never ask again.");
      }
    });
  };
  warmMicIfAllowed();

  // ---- fullscreen toggle (works on iPhone too, where the API doesn't) ----
  var fsBtn = document.getElementById("fsbtn");
  fsBtn.onclick = function () {
    if (liveEl.classList.contains("fs")) {
      liveEl.classList.remove("fs");
      fsBtn.classList.remove("on");
    } else {
      liveEl.classList.add("fs");
      fsBtn.classList.add("on");
      if (liveEl.requestFullscreen) { try { liveEl.requestFullscreen(); } catch (e) {} }
    }
  };

  // ---- system audio (what the PC is playing) ----
  var actx = null, audioOn = false, nextAudioAt = 0, audioStop = false;

  function audioCtx() {
    if (!actx) {
      var C = window.AudioContext || window.webkitAudioContext;
      if (!C) return null;
      actx = new C();
    }
    if (actx.state === "suspended") actx.resume();
    return actx;
  }

  function playPcm(bytes) {
    var ctx = actx; if (!ctx) return;
    var frames = bytes.length >> 2;          // 2 channels * 2 bytes
    if (!frames) return;
    var view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    var buf = ctx.createBuffer(2, frames, 48000);
    var l = buf.getChannelData(0), r = buf.getChannelData(1);
    for (var i = 0; i < frames; i++) {
      l[i] = view.getInt16(i * 4, true) / 32768;
      r[i] = view.getInt16(i * 4 + 2, true) / 32768;
    }
    if (nextAudioAt < ctx.currentTime) nextAudioAt = ctx.currentTime + 0.05;
    if (nextAudioAt - ctx.currentTime > 0.8) nextAudioAt = ctx.currentTime + 0.05; // resync
    var src = ctx.createBufferSource();
    src.buffer = buf; src.connect(ctx.destination); src.start(nextAudioAt);
    nextAudioAt += buf.duration;
  }

  async function startAudio() {
    var ctx = audioCtx(); if (!ctx) return;
    audioOn = true; audioStop = false;
    nextAudioAt = ctx.currentTime + 0.15;
    document.getElementById("sndbtn").classList.add("on");
    setCrossed(false);
    try {
      var resp = await fetch("/api/audio.pcm?t=" + encodeURIComponent(TOKEN));
      if (!resp.ok || !resp.body) throw new Error("no audio");
      var reader = resp.body.getReader();
      while (audioOn) {
        var r = await reader.read();
        if (r.done) break;
        if (r.value) playPcm(r.value);
      }
    } catch (e) {
      if (audioOn) add("sys", "System audio unavailable on this PC.");
    }
    audioOn = false;
    document.getElementById("sndbtn").classList.remove("on");
  }

  function stopAudio() {
    audioOn = false; audioStop = true;
    document.getElementById("sndbtn").classList.remove("on");
    setCrossed(true);
  }

  function setCrossed(muted) {
    var a = document.getElementById("sndx"), b = document.getElementById("sndx2");
    if (a) a.style.display = muted ? "" : "none";
    if (b) b.style.display = muted ? "" : "none";
  }

  document.getElementById("sndbtn").onclick = function () {
    if (audioOn) stopAudio(); else startAudio();
  };
  setCrossed(true);

  // ---- live screen stream ----
  var liveTimer = null, liveMode = "";

  function stopLive() {
    liveOn = false;
    if (liveTimer) { clearInterval(liveTimer); liveTimer = null; }
    liveMode = "";
    liveImg.removeAttribute("src");
    liveEl.style.display = "none";
    liveBtn.classList.remove("on");
    document.getElementById("livenote").textContent = "";
  }

  // Some browsers/proxies never render a multipart MJPEG stream. Fall back to
  // polling whole JPEG snapshots, which is slower but always displays.
  function startSnapshots() {
    if (liveMode === "snap") return;
    liveMode = "snap";
    document.getElementById("livenote").textContent = "(preview mode)";
    var tick = function () {
      if (!liveOn) return;
      var img = new Image();
      img.onload = function () {
        if (liveOn && liveMode === "snap") {
          liveImg.src = this.src;
        }
      };
      img.src = "/api/snap.jpg?t=" + encodeURIComponent(TOKEN) + "&_=" + Date.now();
    };
    tick();
    liveTimer = setInterval(tick, 220);
  }

  liveBtn.onclick = function () {
    if (liveOn) { stopLive(); return; }
    liveOn = true;
    liveMode = "mjpeg";
    liveEl.style.display = "block";
    liveBtn.classList.add("on");
    document.getElementById("livenote").textContent = "connecting…";
    liveImg.src = "/api/stream.mjpg?t=" + encodeURIComponent(TOKEN) + "&_=" + Date.now();
    // If nothing renders in time, switch to snapshot mode automatically.
    setTimeout(function () {
      if (liveOn && liveMode === "mjpeg" && !liveImg.naturalWidth) {
        liveImg.removeAttribute("src");
        startSnapshots();
      }
    }, 5000);
  };
  liveImg.onerror = function () {
    if (!liveOn) return;
    if (liveMode === "mjpeg") startSnapshots();
  };

  // ---- one-off screenshot ----
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