"""AI provider presets.

Every provider is OpenAI-compatible: the app just needs a host URL, a model
name and (optionally) an API key.  Switching providers only rewrites those
config values, so ``core/ollama.py`` needs no provider-specific code.
"""

PROVIDER_ORDER = ["openrouter", "local"]

PROVIDERS = {
    "openrouter": {
        "label": "OpenRouter (cloud)",
        "use_cloud": True,
        "host": "https://openrouter.ai/api/v1/chat/completions",
        "needs_key": True,
        "key_label": "OpenRouter API key",
        "key_hint": "https://openrouter.ai/keys",
        # A vision model is required for PC commands (it reads the screenshot
        # to pick windows, click coordinates, and so on).
        "models": [
            "nvidia/nemotron-3.5-super-vl:free",
            "google/gemma-4-31b-it:free",
            "openrouter/free",
            "thinkingmachines/inkling:free",
        ],
        # Text-only free models for answering general questions.
        "chat_models": [
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "xingchen-agi/xing4.0-29b-a4b:free",
            "nvidia/nemotron-3.5-lightning:free",
        ],
        "reasoning_effort": "",
    },
    "local": {
        "label": "Local Ollama",
        "use_cloud": False,
        "host": "http://localhost:11434/v1/chat/completions",
        "needs_key": False,
        "key_label": "",
        "key_hint": "https://ollama.com/download",
        "models": [
            "qwen2.5vl:3b",
        ],
        "chat_models": [
            "qwen2.5vl:3b",
        ],
        "reasoning_effort": "",
    },
}

DEFAULT_PROVIDER = "openrouter"


def get(provider):
    """Return the preset for *provider*, falling back to OpenRouter."""
    key = (provider or "").strip().lower()
    return PROVIDERS.get(key, PROVIDERS[DEFAULT_PROVIDER])


def known(provider):
    return (provider or "").strip().lower() in PROVIDERS


def chat_model_list(provider):
    preset = get(provider)
    return list(preset.get("chat_models") or preset["models"])


def key_name(provider):
    """Config key that stores the API key for *provider*."""
    return f"{(provider or '').strip().lower()}_key"


def model_name(provider):
    """Config key that stores the last-used model for *provider*."""
    p = (provider or "").strip().lower()
    return "ollama_model" if p == "local" else f"{p}_model"
