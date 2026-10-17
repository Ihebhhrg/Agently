"""AI provider presets.

Every provider is OpenAI-compatible: the app just needs a host URL, a model
name and (optionally) an API key.  Switching providers only rewrites those
config values, so ``core/ollama.py`` needs no provider-specific code.
"""

PROVIDER_ORDER = ["gemini", "openrouter", "local"]

PROVIDERS = {
    "gemini": {
        "label": "Google Gemini (cloud)",
        "use_cloud": True,
        "host": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "needs_key": True,
        "key_label": "Gemini API key",
        "key_hint": "https://aistudio.google.com/apikey",
        "models": [
            "gemini-3.5-flash",
            "gemini-3.8-flash",
            "gemini-3.5-flash-lite",
        ],
        # Gemini 3.x emits thinking tokens unless told not to.
        "reasoning_effort": "none",
    },
    "openrouter": {
        "label": "OpenRouter (cloud)",
        "use_cloud": True,
        "host": "https://openrouter.ai/api/v1/chat/completions",
        "needs_key": True,
        "key_label": "OpenRouter API key",
        "key_hint": "https://openrouter.ai/keys",
        "models": [
            "nvidia/nemotron-3.5-super-vl:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "openrouter/free",
            "google/gemma-4-31b-it:free",
        ],
        "reasoning_effort": "",
    },
    "local": {
        "label": "Local Ollama",
        "use_cloud": False,
        "host": "http://localhost:11434/v1/chat/completions",
        "needs_key": False,
        "key_label": "",
        "key_hint": "",
        "models": [
            "qwen2.5vl:3b",
        ],
        "reasoning_effort": "",
    },
}


def get(provider):
    """Return the preset for *provider*, falling back to Gemini."""
    key = (provider or "").strip().lower()
    return PROVIDERS.get(key, PROVIDERS["gemini"])


def key_name(provider):
    """Config key that stores the API key for *provider*."""
    return f"{(provider or '').strip().lower()}_key"


def model_name(provider):
    """Config key that stores the last-used model for *provider*."""
    p = (provider or "").strip().lower()
    return "ollama_model" if p == "local" else f"{p}_model"
