"""Encrypt the provider API keys at rest using Windows DPAPI.

Keys used to sit in config.ini in the clear. This stores them on disk as
``dpapi:<base64>`` (tied to the current Windows user) while keeping the
plaintext only in memory, so the rest of the app is unchanged.
"""
import base64
import configparser

try:
    import win32crypt
    _HAVE_DPAPI = True
except Exception:  # pywin32 is a hard runtime dependency, so this is just a safety net
    win32crypt = None
    _HAVE_DPAPI = False

PREFIX = "dpapi:"
KEY_FIELDS = ("gemini_key", "openrouter_key", "api_key", "remote_token",
              "remote_devices")
_DESCRIPTION = "Agently"


def protect(text):
    """Plaintext -> ``dpapi:<base64>``. Empty stays empty."""
    text = text or ""
    if not text:
        return ""
    if not _HAVE_DPAPI:
        return text
    blob = win32crypt.CryptProtectData(
        text.encode("utf-8"), _DESCRIPTION, None, None, None, 0
    )
    return PREFIX + base64.b64encode(blob).decode("ascii")


def unprotect(value):
    """``dpapi:<base64>`` -> plaintext. Legacy plaintext is returned unchanged."""
    value = value or ""
    if not value:
        return ""
    if not value.startswith(PREFIX):
        return value
    if not _HAVE_DPAPI:
        return ""
    try:
        blob = base64.b64decode(value[len(PREFIX):])
        _description, data = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
        return data.decode("utf-8")
    except Exception:
        return ""


def is_encrypted(value):
    return bool(value) and str(value).startswith(PREFIX)


def has_plaintext_keys(cfg):
    """True if any key field is set but not yet encrypted (needs migration)."""
    if not cfg.has_section("Main"):
        return False
    for field in KEY_FIELDS:
        if cfg.has_option("Main", field):
            value = cfg["Main"].get(field, "")
            if value and not is_encrypted(value):
                return True
    return False


def decrypt_config(cfg):
    """Replace encrypted key fields with plaintext, in place."""
    if not cfg.has_section("Main"):
        return
    for field in KEY_FIELDS:
        if cfg.has_option("Main", field):
            cfg["Main"][field] = unprotect(cfg["Main"].get(field, ""))


def _encrypted_copy(cfg):
    copy = configparser.ConfigParser()
    for section in cfg.sections():
        copy.add_section(section)
        for key, value in cfg.items(section):
            copy.set(section, key, value)
    if copy.has_section("Main"):
        for field in KEY_FIELDS:
            if copy.has_option("Main", field):
                copy["Main"][field] = protect(copy["Main"].get(field, ""))
    return copy


def save_config(cfg, path):
    """Write *cfg* to *path* with key fields encrypted. Memory is untouched."""
    with open(path, "w", encoding="utf-8") as f:
        _encrypted_copy(cfg).write(f)


def new_token():
    """A fresh access token for the remote web app.

    Short enough to be readable/typed as a fallback (the QR is the normal
    path), while still being 72 bits of entropy - ample for a device on a
    private Tailscale network.
    """
    import secrets as _secrets
    return _secrets.token_urlsafe(9)  # 12 chars
