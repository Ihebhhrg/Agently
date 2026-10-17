import threading


class TTS:
    """Offline text-to-speech using Windows SAPI (free, no internet)."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.enabled = cfg["Main"].getboolean("tts", True)
        self.rate = int(cfg["Main"].get("tts_rate", 1))
        self.volume = int(cfg["Main"].get("tts_volume", 100))
        self._lock = threading.Lock()

    def set_enabled(self, on: bool):
        self.enabled = bool(on)

    def speak(self, text: str):
        if not self.enabled or not text:
            return
        threading.Thread(target=self._speak, args=(text,), daemon=True).start()

    def _speak(self, text: str):
        try:
            import pythoncom
            import win32com.client
            with self._lock:
                pythoncom.CoInitialize()
                try:
                    voice = win32com.client.Dispatch("SAPI.SpVoice")
                    voice.Rate = self.rate
                    voice.Volume = self.volume
                    self._use_female_voice(voice)
                    voice.Speak(text)
                finally:
                    pythoncom.CoUninitialize()
        except Exception as e:
            print(f"TTS error: {e}")

    @staticmethod
    def _use_female_voice(voice):
        try:
            voices = voice.GetVoices()
            female_hints = ("zira", "female", "hazel", "susan", "eva",
                            "samantha", "female voice")
            for i in range(voices.Count):
                token = voices.Item(i)
                desc = token.GetDescription().lower()
                if any(h in desc for h in female_hints):
                    voice.Voice = token
                    return
        except Exception:
            pass

