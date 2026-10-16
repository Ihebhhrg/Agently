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
- If Windows SmartScreen warns about an unknown publisher, choose **More info → Run anyway** (the app is not code-signed).

## Switching AI providers
In **Brain → Provider** you can choose:
- **Gemini** (default, free tier) — paste a Gemini key.
- **OpenRouter** — paste an OpenRouter key; a working free model is pre-set.
- **Local (Ollama)** — if you have Ollama installed, the app starts/stops it on demand.
