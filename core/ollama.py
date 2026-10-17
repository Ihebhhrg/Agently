import requests
import json
import base64

from core.providers import get as get_provider, key_name


class OllamaClient:
    """OpenAI-compatible chat client. Works with local Ollama or any cloud API.

    The provider is chosen in config (``provider``) and only decides the host,
    model, key and whether the local Ollama server must be started on demand.
    """

    def __init__(self, cfg, service=None):
        self.cfg = cfg
        self.service = service
        self.provider = (cfg['Main'].get('provider', 'gemini') or 'gemini').strip().lower()
        preset = get_provider(self.provider)
        self.use_cloud = preset['use_cloud']

        if self.use_cloud:
            self.url = (cfg['Main'].get('api_host', '') or preset['host']).strip()
            self.model = (cfg['Main'].get('cloud_model', '') or preset['models'][0]).strip()
        else:
            self.url = cfg['Main'].get('ollama_host', preset['host']).strip()
            self.model = (cfg['Main'].get('ollama_model', '') or preset['models'][0]).strip()

        self.api_key = ''
        if preset['needs_key']:
            self.api_key = (cfg['Main'].get(key_name(self.provider), '') or '').strip()
            # backward compatibility: older configs stored a single api_key
            if not self.api_key and self.provider == 'gemini':
                self.api_key = (cfg['Main'].get('api_key', '') or '').strip()
        self.temperature = float(cfg['Main'].get('temperature', 0.2))
        self.max_tokens = int(cfg['Main'].get('max_tokens', 800))
        # Only Gemini (a cloud preset with a non-empty value) needs this.
        self.reasoning_effort = preset.get('reasoning_effort', '') if self.use_cloud else ''

    def _encode_image(self, img_path):
        try:
            with open(img_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            return None

    def query(self, prompt: str, img_path: str = None, system: str = None, callback=None) -> str:
        try:
            if not self.use_cloud and self.service is not None:
                if not self.service.ensure_running():
                    reason = (getattr(self.service, "last_error", "") or
                              "the local Ollama server is not available")
                    return f"Error: {reason}"

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            content = [{"type": "text", "text": prompt}]
            if img_path:
                b64 = self._encode_image(img_path)
                if b64:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"}
                    })
            messages.append({"role": "user", "content": content})
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False
            }
            if self.use_cloud and self.reasoning_effort:
                payload["reasoning_effort"] = self.reasoning_effort
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.post(self.url, json=payload, headers=headers, timeout=300)
            if resp.status_code >= 400:
                detail = ""
                try:
                    j = resp.json()
                    detail = (j.get("error", {}) or {}).get("message") if isinstance(j.get("error"), dict) else j.get("error")
                    if not detail:
                        detail = j.get("message") or ""
                except Exception:
                    detail = resp.text[:300]
                return f"Error {resp.status_code}: {detail or resp.reason}"
            data = resp.json()
            if 'choices' in data and data['choices']:
                msg = data['choices'][0].get('message', {})
                if 'content' in msg:
                    return msg['content'].strip()
            return str(data)
        except Exception as e:
            return f"Error: {e}"
