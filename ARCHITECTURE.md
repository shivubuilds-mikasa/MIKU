# Architecture

- `main.py` starts a single-instance PySide6 desktop app.
- `miku/agent.py` sends chat and registered tool calls to local Ollama, then returns tool results for follow-up.
- `miku/tools.py` provides app launching, accessible window inspection, Google searches opened in the user's Mikasa Chrome profile, approved-root file operations, SQLite memory actions, and screenshot/input tools. Chrome's protected regular profile is not read by Miku.
- `miku/memory.py` stores chat turns and searchable facts in local SQLite.
- `miku/ui.py` contains the dark chat UI, recent prompts, model/status controls, speech input/output, and approval dialog.
- `miku_hotkey.py` registers Ctrl+J and either restores the Miku window or launches it.

One selected model coordinates tool use. No cloud model or separate background agent models are used.
