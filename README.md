# Agently v1.0.0

A free Windows voice agent — talk to your PC, it shows what it heard and answers in a floating chat bubble, and it can open apps, manage windows, work with files, set timers, change system settings, and more.

## Requirements
- Windows 10 or 11 (64-bit)
- A microphone
- Internet (for the AI "brain" and, on the Lite build, a one-time voice-model download)
- A **free** Google Gemini API key (see below) — or run a **local model** with no key and no internet at all (see *Offline / local AI with Ollama*).

## Downloads — pick one

| File | Voice model | Size | Best for |
|---|---|---|---|
| `Agently-Setup-Lite.exe` | downloads on first use (needs internet once) | ~135 MB | smallest download |
| `Agently-Setup-Full.exe` | bundled (works offline) | ~550 MB | no first-run download |
| `Agently-Portable-Lite.zip` | downloads on first use | ~194 MB | no install |
| `Agently-Portable-Full.zip` | bundled | ~620 MB | no install, offline |

Installers create a Start Menu shortcut (and offer a desktop shortcut). Portable ZIPs just need to be extracted and `Agently.exe` run.

## First-time setup (2 minutes)
1. Get a free Gemini API key: https://aistudio.google.com/apikey
2. Launch **Agently**.
3. In the main window, open the **Brain** section → set **Provider = Gemini**, paste your key into the **API key** field, and click **Save**.
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
- Your API key is stored only in `config.ini` next to the app, on your own PC.
- No admin rights are needed for installation.
- A command blocklist still refuses obviously destructive commands (`format`, `diskpart`, mass-deletes) even when Run commands is enabled.

## Why might Windows/antivirus warn? (and what to do)
Agently is **not** code-signed (certificates cost money), so Windows may show a warning. This is a **false positive** — the app is safe. To proceed:

- **"Windows protected your PC" (blue):** click **More info → Run anyway**.
- **Windows Security / Defender flags it (red "may be a virus"):** open **Windows Security → Protection history**, find the item, choose **Allow on device** / **Restore**. You can also add the folder to **Virus & threat protection → Exclusions**.
- If in doubt, verify the file integrity against the **SHA-256** hashes below.

> This build removes a common false-positive trigger (a low-level keyboard hook) and adds proper file metadata. If Defender still flags it, please report it as a **false positive** to Microsoft: https://www.microsoft.com/en-us/wdsi/filesubmission

## SHA-256 checksums
```
670e828cabd6a5f6ee4c9807a4f884dadafacd09bb91e8d99144556b13d3afe0  Agently-Setup-Full.exe
ac7b253770de6b307274a736f4eb34f10d7fba51ab1164890a2a1fac98bd4b16  Agently-Setup-Lite.exe
7706df737d2d3417949f4d27ad8ee92a1ca0dc8d0a3897d76680c5ae11ea933d  Agently-Portable-Full.zip
57a468c6c8dd8047f0987717291692b6de89bb83ee0d926386a62f35408311b9  Agently-Portable-Lite.zip
```
Verify on Windows: `certutil -hashfile Agently-Setup-Lite.exe SHA256`

## Switching AI providers
In **Brain → Provider** you can choose:
- **Gemini** (default, free tier) — paste a Gemini key.
- **OpenRouter** — paste an OpenRouter key; a working free model is pre-set.
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

