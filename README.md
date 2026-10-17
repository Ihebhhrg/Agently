# Agently v1.0.0

A free Windows voice agent — talk to your PC, it shows what it heard and answers in a floating chat bubble, and it can open apps, search the web, take screenshots, read/translate the screen, and more.

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

## Notes
- Your API key is stored only in `config.ini` next to the app, on your own PC.
- No admin rights are needed for installation.

## Why might Windows/antivirus warn? (and what to do)
Agently is **not** code-signed (certificates cost money), so Windows may show a warning. This is a **false positive** — the app is safe. To proceed:

- **"Windows protected your PC" (blue):** click **More info → Run anyway**.
- **Windows Security / Defender flags it (red "may be a virus"):** open **Windows Security → Protection history**, find the item, choose **Allow on device** / **Restore**. You can also add the folder to **Virus & threat protection → Exclusions**.
- If in doubt, verify the file integrity against the **SHA-256** hashes below.

> This build removes a common false-positive trigger (a low-level keyboard hook) and adds proper file metadata. If Defender still flags it, please report it as a **false positive** to Microsoft: https://www.microsoft.com/en-us/wdsi/filesubmission

## SHA-256 checksums
```
f438ce715f5293cffbcf08c956105616b75ad39783dd7e613a54bd2d215648ab  Agently-Setup-Full.exe
4031dfa5b210cdfa8c7f705c18130c1d2a4418775b51f96b58b9f9661174bfc9  Agently-Setup-Lite.exe
eb953dbee80e2643116218abbcb3a8410ce6ced5154246c65d9c8eb3eea11333  Agently-Portable-Full.zip
03975449b4c43a295a33851aea2877ad959385a2afb9fad1c1e6d4c849f7c616  Agently-Portable-Lite.zip
```
Verify on Windows: `certutil -hashfile Agently-Setup-Lite.exe SHA256`

## Switching AI providers
In **Brain → Provider** you can choose:
- **Gemini** (default, free tier) — paste a Gemini key.
- **OpenRouter** — paste an OpenRouter key; a working free model is pre-set.
- **Local (Ollama)** — if you have Ollama installed, the app starts/stops it on demand.
