import requests
import json
import base64

from core.providers import get as get_provider, key_name


class OllamaClient:
    """OpenAI-compatible chat client. Works with local Ollama or any cloud API.

    The provider is chosen in config (``provider``) and only decides the host,
    model, key and whether the local Ollama server must be started on demand.
    Pass ``provider_override`` to build a second client aimed at a different
    provider - that is how chat questions get routed to a stronger model while
    PC commands stay on the configured one.
    """

    def __init__(self, cfg, service=None, provider_override=None, model_override=None):
        self.cfg = cfg
        self.service = service
        self.provider = (provider_override
                         or cfg['Main'].get('provider', 'openrouter')
                         or 'openrouter').strip().lower()
        preset = get_provider(self.provider)
        self.use_cloud = preset['use_cloud']

        if self.use_cloud:
            self.url = (cfg['Main'].get('api_host', '') or preset['host']).strip()
            self.model = (model_override
                          or cfg['Main'].get('cloud_model', '')
                          or preset['models'][0]).strip()
        else:
            self.url = cfg['Main'].get('ollama_host', preset['host']).strip()
            self.model = (model_override
                          or cfg['Main'].get('ollama_model', '')
                          or preset['models'][0]).strip()

        self.api_key = ''
        if preset['needs_key']:
            self.api_key = (cfg['Main'].get(key_name(self.provider), '') or '').strip()
        self.temperature = float(cfg['Main'].get('temperature', 0.2))
        self.max_tokens = int(cfg['Main'].get('max_tokens', 800))
        self.reasoning_effort = preset.get('reasoning_effort', '') if self.use_cloud else ''

    def _encode_image(self, img_path):
        try:
            with open(img_path, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            return None

    def query(self, prompt: str, img_path: str = None, system: str = None,
              history=None, max_tokens=None, temperature=None) -> str:
        """Single-turn query with optional image and prior turns.

        ``history`` is a list of {'role','content'} dicts that get inserted
        before the current prompt so follow-up questions have context.
        """
        try:
            if not self.use_cloud and self.service is not None:
                if not self.service.ensure_running():
                    reason = (getattr(self.service, "last_error", "") or
                              "the local Ollama server is not available")
                    return f"Error: {reason}"

            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            for h in (history or [])[-12:]:
                role = h.get("role", "user")
                content = h.get("content", "")
                if role != "system" and content:
                    messages.append({"role": role, "content": content})
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
                "temperature": self.temperature if temperature is None else temperature,
                "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
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
