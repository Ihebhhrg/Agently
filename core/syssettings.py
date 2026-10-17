import ctypes

from core import shell


def set_brightness(level):
    try:
        level = max(0, min(100, int(level)))
    except (TypeError, ValueError):
        return False, "Brightness must be a number from 0 to 100."
    cmd = (
        "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1,{level})"
    )
    ok, out = shell.run(cmd, kind="powershell")
    if ok:
        return True, f"Brightness set to {level}%"
    return False, "Could not change brightness (this works on built-in laptop displays)."


def set_dark_mode(on):
    import winreg
    on = bool(on)
    # 0 = dark, 1 = light
    value = 0 if on else 1
    path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as k:
            for name in ("AppsUseLightTheme", "SystemUsesLightTheme"):
                winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, value)
    except Exception as e:
        return False, f"Could not change theme: {e}"
    _broadcast_setting_change()
    return True, f"Dark mode {'on' if on else 'off'}"


def _broadcast_setting_change():
    try:
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x1A
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, "ImmersiveColorSet", 0, 100, None
        )
    except Exception:
        pass


def set_wifi(on):
    state = "Enable" if on else "Disable"
    cmd = (
        "Get-NetAdapter -Physical | "
        "Where-Object {$_.MediaType -eq 'Native 802.11'} | "
        f"{state}-NetAdapter -Confirm:$false"
    )
    ok, out = shell.run(cmd, kind="powershell", elevated=True)
    if ok:
        return True, f"Wi-Fi {'on' if on else 'off'}."
    return False, out


def set_bluetooth(on):
    state = "Enable" if on else "Disable"
    cmd = f"Get-PnpDevice -Class Bluetooth | {state}-PnpDevice -Confirm:$false"
    ok, out = shell.run(cmd, kind="powershell", elevated=True)
    if ok:
        return True, f"Bluetooth {'on' if on else 'off'}."
    return False, out
