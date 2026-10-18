# Agently v1.0.0

A free Windows voice agent — talk to your PC, it shows what it heard and answers in a floating chat bubble, and it can open apps, manage windows, work with files, set timers, change system settings, and more.

## Requirements
- Windows 10 or 11 (64-bit)
- A microphone
- Internet (for the AI "brain" and, on the Lite build, a one-time voice-model download)
- A **free** OpenRouter API key (see below) — or run a **local model** with no key and no internet at all (see *Offline / local AI with Ollama*).

## Downloads — pick one

| File | Voice model | Size | Best for |
|---|---|---|---|
| `Agently-Setup-Lite.exe` | downloads on first use (needs internet once) | ~138 MB | smallest download |
| `Agently-Setup-Full.exe` | bundled (works offline) | ~553 MB | no first-run download |
| `Agently-Portable-Lite.zip` | downloads on first use | ~197 MB | no install |
| `Agently-Portable-Full.zip` | bundled | ~623 MB | no install, offline |

Installers create a Start Menu shortcut (and offer a desktop shortcut). Portable ZIPs just need to be extracted and `Agently.exe` run.

## First-time setup (2 minutes)
1. Get a free OpenRouter API key: https://openrouter.ai/keys
2. Launch **Agently**.
3. In the main window, open the **Brain** section → set **Provider = OpenRouter**, paste your key into the **API key** field, and click **Save**.
4. In **Microphone**, pick your microphone from the dropdown (if you speak and nothing is heard, try another device).
5. Hold the push-to-talk hotkey (**Alt+Shift+V** by default) and talk, or switch the mode to always-on.

## Permissions — what it may do
On first launch Agently asks for permission and you choose **Allow full control** or **Keep me safe**. You can change any of this later in the **Permissions** panel.

| Group | Lets Agently | Default |
|---|---|---|
| Apps & windows | close, focus and list open windows | on |
| Files & folders | open, create, move, copy, delete (to Recycle Bin) | on |
| Clipboard & screenshots | read/write clipboard, capture screen | on |
| Timers & reminders | set and cancel timers | on |
| System settings | brightness, Wi-Fi, Bluetooth, dark mode | on |
| Power actions | shut down, restart, sleep, log off | off until granted |
| Run commands | execute shell commands and scripts | off until granted |

**Power actions and deletions always ask you to say "yes" first** (you can turn this off in Permissions).

### Examples you can say
- "close chrome" · "switch to notepad" · "show the desktop" · "what windows are open"
- "open my downloads" · "make a folder called notes on my desktop" · "move report.pdf to documents" · "delete test.txt"
- "what's in my clipboard" · "copy hello to the clipboard" · "take a screenshot"
- "set a timer for 5 minutes" · "remind me in 10 minutes to stretch" · "cancel my timers"
- "shut down my pc" · "restart my computer" · "put my pc to sleep" · "log me off"
- "set brightness to 50" · "enable dark mode" · "turn off wifi" · "turn on bluetooth"
- "run ipconfig"

### Admin actions
A few actions (Wi-Fi/Bluetooth adapter, some system settings) need administrator rights. Windows will show a **UAC prompt** only at that moment — the app itself stays non-admin.

## Notes
- Your API key is stored only in `config.ini` next to the app, on your own PC, **encrypted with Windows DPAPI** (only your Windows account can decrypt it).
- No admin rights are needed for installation.
- A command blocklist still refuses obviously destructive commands (`format`, `diskpart`, mass-deletes) even when Run commands is enabled.

## Talking to it (chat vs. commands)
Agently tells your questions and your commands apart automatically:
- **A question** ("what is quantum tunneling?") skips the screenshot entirely, so replies are faster and cheaper, and it answers on any topic.
- **A command** ("open notepad", "shut down") still goes through the action engine with a screenshot, so it can see what you're looking at.
- **"Answers questions with"** in the Brain panel lets you route questions to a different, stronger model than the one handling commands — handy if commands run on the free local model while questions use a big cloud model.
- It **remembers the last few messages**, so follow-ups like "and what about the other one?" work. Press **Forget chat** to clear it.

## Why might Windows/antivirus warn? (and what to do)
Agently is **not** code-signed (certificates cost money), so Windows may show a warning. This is a **false positive** — the app is safe. To proceed:

- **"Windows protected your PC" (blue):** click **More info → Run anyway**.
- **Windows Security / Defender flags it (red "may be a virus"):** open **Windows Security → Protection history**, find the item, choose **Allow on device** / **Restore**. You can also add the folder to **Virus & threat protection → Exclusions**.
- If in doubt, verify the file integrity against the **SHA-256** hashes below.

> This build removes a common false-positive trigger (a low-level keyboard hook) and adds proper file metadata. If Defender still flags it, please report it as a **false positive** to Microsoft: https://www.microsoft.com/en-us/wdsi/filesubmission

## SHA-256 checksums
```
d0171e3e089400f927e42cc18496e45c68747ed2d893b2dc6542a4a21924b28e  Agently-Setup-Full.exe
19a3341a7e5e1aa27ae73de81346506b8d468c25e7afbf6080c383fc293a1b2c  Agently-Setup-Lite.exe
ed689b63a3058c6a71a49c8680625e177c3893e4b183cbc42667bc0004252092  Agently-Portable-Full.zip
e6ed59022865c7e2a5ccc7b537e28dbb072b23a2d36fe0c18112c8e94c50a716  Agently-Portable-Lite.zip
```
Verify on Windows: `certutil -hashfile Agently-Setup-Lite.exe SHA256`

## Switching AI providers
In **Brain → Provider** you can choose:
- **OpenRouter** (default) — paste a free OpenRouter key. Uses free (`:free`) models.
- **Local Ollama** — run a model **entirely offline** on your own PC, with no API key and no data leaving the machine. See the section below.

Two separate models, because they do different jobs:
- **Model** (commands) — `nvidia/nemotron-3.5-super-vl:free`. It must understand images, because it reads your screenshot to decide which window to click.
- **Question model** (chat) — `nvidia/nemotron-3-ultra-550b-a55b:free`, a much larger, text-only model. Bigger models are slower, so if a reply feels slow, switch this to `nvidia/nemotron-3-super-120b-a12b:free` (same answers, ~1 s instead of ~20 s).

Free OpenRouter models come and go. If a model stops working, the app automatically falls back to the one it's using for commands.
- **Local (Ollama)** — run a model **entirely offline** on your own PC, with no API key and no data leaving the machine. See the section below.

## Offline / local AI with Ollama
Agently can run its "brain" locally through [Ollama](https://ollama.com), so it works with **no internet, no API key, and nothing sent to the cloud**. The app starts Ollama when needed and stops it again when idle — and it never shuts down an Ollama server you started yourself.

**1. Install Ollama**
Download and install it from https://ollama.com/download. The standard install location is detected automatically; the **Install Ollama** button in the Brain section opens this page.

**2. Download a vision model** (one-time, needs internet)
Open PowerShell and pull the model:
```
ollama pull qwen2.5vl:3b
```
`qwen2.5vl:3b` is small and runs well on ~6 GB GPUs and most CPUs. With more VRAM you can go bigger, e.g. `ollama pull qwen2.5vl:7b` or `ollama pull llava:7b`.

**3. Point Agently at it**
In the main window open **Brain → Provider → Local Ollama** and click **Save**. Agently starts Ollama if it isn't running, and the **Model** dropdown lists the models you have installed — pick one (e.g. `qwen2.5vl:3b`).

That's it. Hold **Alt+Shift+V** and talk — everything runs on your PC.

**Troubleshooting**
- **"Ollama not found"** — the app auto-detects the standard install. If you installed it elsewhere, set `ollama_exe = <full path to ollama.exe>` in `config.ini` and restart.
- **"model not found"** — pull it first (`ollama pull qwen2.5vl:3b`); the name in the Model box must match exactly.
- **First reply is slow** — the model loads into memory on the first request; later replies are faster.
- **Status line** shows `Local Ollama — running ✔` when it's up, or `stopped (starts on use)`.

## Control it from your phone
Agently serves a small mobile web app so you can talk to your PC, watch its screen and run commands while you're away. It runs over your **private [Tailscale](https://tailscale.com) network**, so **no ports are opened on your router** and nothing is exposed to the public internet.

### Setup — about 5 minutes

**On your PC**
1. Install Agently, then install **Tailscale** for Windows and sign in.
2. In the Agently window tick **Enable remote access**. A QR code appears.
3. Click **Set up HTTPS**. The first time, Tailscale asks you to switch on
   HTTPS serving for your network (one-off, for everyone on that network) —
   Agently opens that page for you. Enable it, then press **Set up HTTPS** again.

**On your phone**
4. Install the **Tailscale** app and sign in with the **same account**.
5. Make sure Tailscale shows as **connected**.
6. **Scan the QR code** with the phone's camera (or open the `https://…ts.net`
   link Agently shows). You are signed in automatically — no token to type.
7. Tap the orange mic and **allow microphone access**. You are asked once, ever.
8. Optional: "Add to Home Screen" so it opens like a normal app.

### Using it
- 🎙 **Orange mic** — tap to start, tap again to send.
- 🖥 **Monitor icon** — watch your PC screen live, with a fullscreen button.
- 🔊 **Speaker icon** — hear whatever your PC is playing.
- 📷 **Camera icon** — take a one-off screenshot (it appears in the chat).
- ⚠️ **Yes / Cancel** — anything risky (running a command, shutdown, deleting a
  file, typing or clicking on your PC) waits for you to tap **Yes**.

### Giving another person access
Click **QR for another phone**, give it a name, and scan the new code. Each
phone gets its **own token**, so you can **Revoke** one without affecting the
others. Up to 6 devices.

### If something isn't working
| Symptom | Fix |
|---|---|
| Orange banner "Microphone needs a secure (https) address" | Press **Set up HTTPS** on the PC and open the `https://…ts.net` link. Browsers block the mic on plain http. |
| Page says "offline" | Tailscale isn't connected on the phone. |
| "Bad token" | That phone was revoked — scan a fresh QR. |
| Screen view blank, header says "preview mode" | Your browser won't render MJPEG streaming; the fallback still shows the screen, just less smoothly. |

### How it stays safe
- The server binds only to your Tailscale interface (plus loopback), and every
  request needs a per-device token stored encrypted (Windows DPAPI).
- Risky actions are confirm-gated on the phone, so nothing dangerous runs from
  a typo or a misheard word. Confirmations expire after 3 minutes.
- The Catastrophic-command blocklist still applies to shell commands.

