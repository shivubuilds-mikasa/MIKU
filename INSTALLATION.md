# Installation

## Requirements

- Windows 11
- Python 3.13
- [Ollama for Windows](https://ollama.com/download)
- One of the models listed in Miku's model menu

## Setup

From PowerShell in the project folder:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen2.5:7b
python main.py
```

Ollama must be running at `http://localhost:11434`. Miku defaults to `qwen2.5:7b`; select another installed model in the app or set `MIKU_MODEL` before launch.

## Ctrl + J and shortcuts

Run `Install Miku Hotkey.ps1` once to add a per-user Startup shortcut. The listener starts at sign-in and opens or focuses Miku when you press **Ctrl + J**. It does not install a service or require administrator rights.

Run `Create Miku Shortcut.ps1` to add a Desktop shortcut. Alternatively, launch `Launch Miku.bat` from File Explorer.

## Voice

Push-to-talk records a six-second clip in memory and transcribes it locally with faster-whisper. The `base` model may download the first time voice input is used. Replies use the Windows SAPI voice installed on the PC.

## Configuration

- `MIKU_MODEL`: initial model name; default `qwen2.5:7b`.
- `MIKU_OLLAMA_URL`: Ollama API base URL; default `http://localhost:11434`.

The legacy `JARVIS_MODEL` and `JARVIS_OLLAMA_URL` variables are also recognized.
