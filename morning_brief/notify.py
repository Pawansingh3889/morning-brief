"""Cross-platform notification dispatch.

Windows uses winotify when installed. Linux and WSL try wsl-notify-send
first (to bridge to Windows toast) and fall back to notify-send on native
desktops. Print-to-stdout is the last resort so nothing goes silent.
"""
from __future__ import annotations

import platform
import subprocess


def send(title: str, body: str) -> bool:
    system = platform.system()
    if system == "Windows":
        return _notify_windows(title, body)
    if system == "Linux":
        return _notify_linux(title, body)
    print(f"{title}: {body}")
    return False


def _notify_windows(title: str, body: str) -> bool:
    try:
        from winotify import Notification  # type: ignore[import-not-found]
    except ImportError:
        print(f"{title}: {body}")
        return False
    Notification(app_id="Morning Brief", title=title, msg=body).show()
    return True


def _notify_linux(title: str, body: str) -> bool:
    for cmd in (
        ["wsl-notify-send.exe", title, body],
        ["notify-send", title, body],
    ):
        try:
            subprocess.run(cmd, check=False, timeout=5)
            return True
        except FileNotFoundError:
            continue
    print(f"{title}: {body}")
    return False
