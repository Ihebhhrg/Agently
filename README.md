# Agently v1.0.0

A free Windows voice agent — talk to your PC, it shows what it heard and answers in a floating chat bubble, and it can open apps, manage windows, work with files, set timers, change system settings, and more.

## Requirements
- Windows 10 or 11 (64-bit)
- A microphone
- Internet (for the AI "brain" and, on the Lite build, a one-time voice-model download)
- A **free** Google Gemini API key (see below)

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
810a2bf7b2996346d205b59af116b81a482e09c10ec02a8a9e19550bcb368d94  Agently-Setup-Full.exe
921689118bd159d309251ce9886c69ce9d43e7ee8f3edd41104ac204fbbd9f52  Agently-Setup-Lite.exe
0251fe23398effcf744f581a47d722ad202e35afefeadb3191124003667d3408  Agently-Portable-Full.zip
a873b07ae85209ccbba6128ee3b89583478b9d24c33296614c2aca5b0c37a2a5  Agently-Portable-Lite.zip
```
Verify on Windows: `certutil -hashfile Agently-Setup-Lite.exe SHA256`

## Switching AI providers
In **Brain → Provider** you can choose:
- **Gemini** (default, free tier) — paste a Gemini key.
- **OpenRouter** — paste an OpenRouter key; a working free model is pre-set.
- **Local (Ollama)** — if you have Ollama installed, the app starts/stops it on demand.
