"""Per-user Ctrl+J listener; only local Ollama API checks and no shell execution."""
import ctypes
import os
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
APP = ROOT / "main.py"
PYTHONW = ROOT / ".venv" / "Scripts" / "pythonw.exe"
LOG = ROOT / "data" / "hotkey.log"
WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002
OLLAMA_URL = os.getenv("MIKU_OLLAMA_URL", os.getenv("JARVIS_OLLAMA_URL", "http://localhost:11434")).rstrip("/")
_ollama_process = None


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


def _ollama_ready():
    try:
        with urlopen(f"{OLLAMA_URL}/api/tags", timeout=1) as response:
            return response.status == 200
    except Exception:
        return False


def ensure_ollama():
    """Start the installed local Ollama server when Ctrl+J is pressed, if needed."""
    global _ollama_process
    host = urlparse(OLLAMA_URL).hostname
    if host not in {"localhost", "127.0.0.1", "::1"}:
        return  # Never try to start a local process for a remote Ollama endpoint.
    if _ollama_ready():
        return

    executable = shutil.which("ollama")
    if not executable:
        candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        if candidate.is_file():
            executable = str(candidate)
    if not executable:
        log("Ollama is not responding and ollama.exe was not found; Miku will still open.")
        return

    try:
        _ollama_process = subprocess.Popen(
            [executable, "serve"],
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
    except Exception as exc:
        log(f"Could not start Ollama: {exc}")
        return

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if _ollama_ready():
            log("Ollama API ready; opening Miku.")
            return
        time.sleep(0.5)
    log("Ollama did not become ready within 20 seconds; Miku will still open.")


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
                ensure_ollama()
                show_or_launch()
    finally:
        user32.UnregisterHotKey(None, 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
