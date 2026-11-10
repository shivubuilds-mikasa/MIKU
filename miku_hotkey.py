"""Per-user Ctrl+J listener. No admin rights, shell execution, or network access."""
import ctypes
import subprocess
import sys
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "main.py"
PYTHONW = ROOT / ".venv" / "Scripts" / "pythonw.exe"
LOG = ROOT / "data" / "hotkey.log"
WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND), ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM), ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD), ("pt", POINT),
        ("lPrivate", wintypes.DWORD),
    ]


def log(message):
    try:
        LOG.parent.mkdir(exist_ok=True)
        with LOG.open("a", encoding="utf-8") as stream:
            stream.write(message + "\n")
    except OSError:
        pass


def show_or_launch():
    user32 = ctypes.windll.user32
    found = []
    enum_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length:
                title = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title, length + 1)
                if title.value == "Miku":
                    found.append(hwnd)
                    return False
        return True

    user32.EnumWindows(enum_type(visit), 0)
    if found:
        user32.ShowWindow(found[0], 9)  # SW_RESTORE
        user32.SetForegroundWindow(found[0])
        return
    try:
        subprocess.Popen([str(PYTHONW), str(APP)], cwd=str(ROOT), close_fds=True)
    except Exception as exc:
        log(f"Could not launch Miku: {exc}")


def main():
    user32 = ctypes.windll.user32
    if not user32.RegisterHotKey(None, 1, MOD_CONTROL, ord("J")):
        log("Ctrl+J listener could not register the hotkey (it may already be in use).")
        return 1
    log("Ctrl+J listener ready.")
    message = MSG()
    try:
        while True:
            result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result <= 0:
                break
            if message.message == WM_HOTKEY and message.wParam == 1:
                show_or_launch()
    finally:
        user32.UnregisterHotKey(None, 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
