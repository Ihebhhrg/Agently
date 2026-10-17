import subprocess

# Catastrophic patterns that are refused even though 'run' is confirm-free.
# These could wipe the machine if a mis-transcribed or injected command slipped through.
_BLOCKED = [
    "format ", "format/", "diskpart", "clean all", "clean disk",
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", "cipher /w",
    "vssadmin delete", "wbadmin delete", "bcdedit",
    "reg delete hklm",
    "del /f /s /q c:\\", "del /f /s /q %systemdrive%",
    "rd /s /q c:\\", "rmdir /s /q c:\\",
    "remove-item -recurse c:\\", "remove-item -recurse -force c:\\",
    "remove-item c:\\windows", "remove-item c:\\users",
    ":(){ :|:&", "fork bomb",
]


def is_blocked(command):
    low = str(command or "").lower()
    for bad in _BLOCKED:
        if bad in low:
            return bad
    return None


def run(command, kind="cmd", elevated=False, timeout=60):
    """Run a shell command. Returns (ok, output)."""
    command = (command or "").strip()
    if not command:
        return False, "No command given."
    bad = is_blocked(command)
    if bad:
        return False, f"Refused a potentially destructive command (matched '{bad}')."

    kind = (kind or "cmd").lower()
    if kind in ("powershell", "ps", "pwsh"):
        args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
    else:
        args = ["cmd", "/c", command]

    if elevated:
        # Re-launch through UAC. Output cannot be captured from the elevated process.
        ps = (
            "Start-Process -Verb RunAs -FilePath "
            + ("'powershell'" if kind in ("powershell", "ps", "pwsh") else "'cmd'")
            + " -ArgumentList "
            + ("'-NoProfile','-Command','{c}'" if kind in ("powershell", "ps", "pwsh")
               else "'/c','{c}'")
        )
        ps = ps.replace("{c}", command.replace("'", "''"))
        try:
            subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", ps],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return True, "Started (you may need to approve the Windows prompt)."
        except Exception as e:
            return False, f"Could not elevate: {e}"

    try:
        p = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        out = (p.stdout or "") + (p.stderr or "")
        out = out.strip()
        ok = p.returncode == 0
        if not out:
            out = "Done." if ok else f"Exited with code {p.returncode}"
        return ok, out[:2000]
    except subprocess.TimeoutExpired:
        return False, "Command timed out."
    except Exception as e:
        return False, f"Command failed: {e}"
