"""Per-device access tokens for the remote web app.

Each phone gets its own token (and its own QR). That way you can hand the
QR to one person without it also working on someone else's phone, and you
can revoke a single device without locking yourself out.

Stored as an encrypted JSON list under the ``remote_devices`` config key.
The older single ``remote_token`` is still honoured so existing phones keep
working, and can be migrated into the list.
"""
import json
import time

from utils.secretstore import new_token

MAX_DEVICES = 6
_FIELD = "remote_devices"


def load(cfg):
    """Return the list of paired devices (never raises)."""
    raw = cfg["Main"].get(_FIELD, "") or ""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [d for d in data if isinstance(d, dict) and d.get("token")]


def write(cfg, devices):
    """Update the in-memory config; the caller persists it with save_config."""
    cfg["Main"][_FIELD] = json.dumps(devices)
    return devices


def migrate_legacy(cfg):
    """Fold an old single-token config into the device list (once)."""
    devices = load(cfg)
    legacy = cfg["Main"].get("remote_token", "") or ""
    if legacy and legacy not in [d["token"] for d in devices]:
        devices.insert(0, {
            "id": legacy[:8],
            "name": "First phone",
            "token": legacy,
            "created": int(time.time()),
        })
        write(cfg, devices)
    return devices


def add(cfg, name=""):
    """Add a device and return it."""
    devices = load(cfg)
    dev = {
        "id": new_token()[:8].replace("-", "").replace("_", ""),
        "name": name or ("Phone %d" % (len(devices) + 1)),
        "token": new_token(),
        "created": int(time.time()),
    }
    devices.append(dev)
    # keep the newest MAX_DEVICES
    devices.sort(key=lambda d: d.get("created", 0))
    devices = devices[-MAX_DEVICES:]
    write(cfg, devices)
    return dev


def remove(cfg, dev_id):
    devices = [d for d in load(cfg) if d.get("id") != dev_id]
    write(cfg, devices)
    return devices


def valid_tokens(cfg):
    """Every token the server should accept (devices + legacy)."""
    toks = {d["token"] for d in load(cfg)}
    legacy = cfg["Main"].get("remote_token", "") or ""
    if legacy:
        toks.add(legacy)
    return toks


def describe(dev):
    when = dev.get("created", 0)
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(when)) if when else "?"
    return f"{dev.get('name') or 'Phone'} — added {stamp}"