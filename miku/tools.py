import os, subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
import shutil
import pyautogui
import pygetwindow
from pywinauto import Desktop
from .config import ALLOWED_ROOTS
from .memory import add_memory, search_memory, delete_memory, clear_history

_launched_processes=[]
CHROME_PROFILE_NAME="Mikasa"

def _chrome_exe():
    candidates=[
        shutil.which("chrome"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    return next((p for p in candidates if p and Path(p).is_file()),None)

def _chrome_profile_directory():
    """Resolve the Chrome profile by its visible name, without reading cookies or page data."""
    import json
    local_state=Path(os.environ.get("LOCALAPPDATA", ""))/"Google"/"Chrome"/"User Data"/"Local State"
    try:
        data=json.loads(local_state.read_text(encoding="utf-8"))
        profiles=data.get("profile",{}).get("info_cache",{})
        for directory,info in profiles.items():
            if info.get("name", "").casefold()==CHROME_PROFILE_NAME.casefold():
                return directory
    except (OSError, ValueError, TypeError):
        pass
    raise RuntimeError(f'Chrome profile "{CHROME_PROFILE_NAME}" was not found.')

def _open_chrome_url(url):
    """Open a URL in the user's actual Chrome profile without automating its profile data."""
    chrome=_chrome_exe()
    if not chrome: raise RuntimeError("Google Chrome was not found on this computer.")
    profile=_chrome_profile_directory()
    _launched_processes.append(subprocess.Popen(
        [chrome,f"--profile-directory={profile}","--new-window",url],shell=False
    ))

def safe_path(raw):
    p = Path(os.path.expandvars(raw)).expanduser().resolve()
    if not any(p == r.resolve() or r.resolve() in p.parents for r in ALLOWED_ROOTS):
        raise ValueError("Path is outside Miku approved workspaces (Documents, Desktop, Downloads, and the Miku project).")
    return p

def launch_app(name):
    known = {"edge":"msedge", "notepad":"notepad", "calculator":"calc", "vscode":"code", "vs code":"code", "explorer":"explorer"}
    key=name.lower().strip()
    if key=="chrome":
        _open_chrome_url("https://www.google.com")
        return f'Opened Google Chrome with the "{CHROME_PROFILE_NAME}" profile on Google.'
    if key not in known: raise ValueError("Supported app aliases: Chrome, Edge, Notepad, Calculator, VS Code, Explorer.")
    _launched_processes.append(subprocess.Popen([known[key]], shell=False))
    return f"Launched {name}."

def open_url(url):
    if not url.startswith(("http://", "https://")): url="https://"+url
    _open_chrome_url(url)
    return f'Opened {url} in the user\'s Google Chrome profile "{CHROME_PROFILE_NAME}". The page is visible in Chrome.'

def browser_search(query):
    """Open Google results in the user's visible Chrome profile."""
    url="https://www.google.com/search?q="+quote_plus(query)
    _open_chrome_url(url)
    return f'Opened Google results for {query!r} in the Chrome profile "{CHROME_PROFILE_NAME}". Miku cannot read page contents from Chrome\'s protected main profile; inspect the visible results in Chrome.'

def save_memory(content): add_memory(content); return "Saved to local Miku memory."
def recall_memory(query): return "\n".join(search_memory(query)) or "No matching saved memories."
def forget_memory(query): return f"Removed {delete_memory(query)} matching saved memories."
def clear_conversation_history(): clear_history(); return "Cleared local conversation history."

def read_file(path):
    p=safe_path(path)
    if not p.is_file(): raise ValueError("File does not exist.")
    if p.stat().st_size > 1_000_000: raise ValueError("File exceeds 1 MB limit.")
    return p.read_text(encoding="utf-8", errors="replace")

def list_files(path):
    p=safe_path(path)
    if not p.is_dir(): raise ValueError("Folder does not exist.")
    return "\n".join(("[DIR] " if x.is_dir() else "[FILE] ")+x.name for x in sorted(p.iterdir(),key=lambda z:(not z.is_dir(),z.name.lower()))[:300]) or "Folder is empty."

def create_file(path, content):
    p=safe_path(path); p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        backup=p.with_name(p.name+".miku-backup-"+datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        backup.write_bytes(p.read_bytes())
    p.write_text(content, encoding="utf-8"); return f"Wrote {p}"+(f"; previous version saved at {backup}" if 'backup' in locals() else "")

def move_file(source,destination):
    src=safe_path(source); dst=safe_path(destination)
    if not src.is_file(): raise ValueError("Source file does not exist.")
    if dst.exists(): raise ValueError("Destination already exists; refusing to overwrite.")
    dst.parent.mkdir(parents=True,exist_ok=True); src.rename(dst); return f"Moved {src} to {dst}. This can be reversed by moving it back."

def screenshot():
    p=Path.home()/"Pictures"/"Miku-screenshot.png"; p.parent.mkdir(exist_ok=True); pyautogui.screenshot().save(p); return str(p)

def click(x,y): pyautogui.click(int(x),int(y)); return f"Clicked at {x},{y}."
def type_text(text): pyautogui.write(text, interval=0.01); return "Typed text."
def hotkey(keys): pyautogui.hotkey(*keys); return "Pressed " + "+".join(keys)
def scroll(amount): pyautogui.scroll(int(amount)); return "Scrolled."

def list_windows():
    titles=[t for t in pygetwindow.getAllTitles() if t.strip()]
    return "\n".join(titles) or "No open windows found."

def switch_window(title):
    matches=[w for w in pygetwindow.getAllWindows() if title.lower() in w.title.lower()]
    if not matches: raise ValueError("No window title contains that text.")
    matches[0].activate(); return f"Activated window: {matches[0].title}"

def inspect_window(title):
    wins=[w for w in Desktop(backend="uia").windows() if title.lower() in w.window_text().lower()]
    if not wins: raise ValueError("No accessible window title contains that text.")
    controls=wins[0].descendants()[:150]
    return "\n".join(f"{c.element_info.control_type}: {c.window_text()[:180]}" for c in controls if c.window_text() or c.element_info.control_type in ("Button","Edit","ListItem","ComboBox"))

TOOLS={
 "launch_app": ("Launch a known desktop app: chrome, edge, notepad, calculator, vscode, explorer", {"name":"string"}, launch_app),
 "open_url": ("Open a URL in the user's Google Chrome Mikasa profile; pages are displayed for the user", {"url":"string"}, open_url),
 "browser_search": ("Open Google search results in the user's Chrome Mikasa profile; Miku cannot read the protected profile page contents", {"query":"string"}, browser_search),
 "save_memory": ("Save a useful user preference or project fact to local SQLite memory", {"content":"string"}, save_memory),
 "search_memory": ("Search saved local Miku memories", {"query":"string"}, recall_memory),
 "forget_memory": ("Delete saved memories matching the user's explicit request", {"query":"string"}, forget_memory),
 "clear_conversation_history": ("Delete all local conversation messages when explicitly requested", {}, clear_conversation_history),
 "read_file": ("Read a UTF-8 text file in approved workspaces", {"path":"string"}, read_file),
 "list_files": ("List files and folders in approved workspaces", {"path":"string"}, list_files),
 "create_file": ("Create or edit a text file in approved workspaces; overwrites create a timestamped backup", {"path":"string","content":"string"}, create_file),
 "move_file": ("Move a file between approved workspaces without overwriting; reversible", {"source":"string","destination":"string"}, move_file),
 "list_windows": ("List open windows", {}, list_windows),
 "switch_window": ("Activate an open window by part of its title", {"title":"string"}, switch_window),
 "inspect_window": ("Inspect accessible UI controls in an open window by title", {"title":"string"}, inspect_window),
 "screenshot": ("Capture the screen and save a screenshot", {}, screenshot),
 "click": ("Click desktop coordinates (use screenshot first)", {"x":"integer","y":"integer"}, click),
 "type_text": ("Type text into the active window", {"text":"string"}, type_text),
 "hotkey": ("Press keyboard shortcut, keys array e.g. ['ctrl','l']", {"keys":"array"}, hotkey),
 "scroll": ("Scroll up/down at cursor; positive up", {"amount":"integer"}, scroll),
}

def ollama_tools():
    result=[]
    for name,(desc,props,_) in TOOLS.items():
        result.append({"type":"function","function":{"name":name,"description":desc,"parameters":{"type":"object","properties":{k:{"type":v} for k,v in props.items()},"required":list(props),"additionalProperties":False}}})
    return result

def execute(name,args):
    if name not in TOOLS: raise ValueError("Unknown tool")
    if name in ("click","type_text","hotkey","scroll"):
        # Coordinate and input actions are constrained to active user session; confirmation policy belongs to UI for autonomous plans.
        pass
    return TOOLS[name][2](**args)
