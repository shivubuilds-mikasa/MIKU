# Troubleshooting

- **Ollama offline:** start Ollama and check `http://localhost:11434/api/tags`.
- **Model unavailable:** verify the exact model tag with `ollama list`; restart Miku after pulling models.
- **Slow inference:** select `qwen3.5:2b`; Ollama may share limited VRAM with the Windows desktop.
- **Ctrl+J does not work:** open `Install Miku Hotkey.ps1` from the project folder; ensure no other app already owns Ctrl+J. Check `data/hotkey.log`.
- **Google search opens but Miku cannot summarize it:** search results open in the Mikasa Chrome profile for you to review. Chrome blocks automation of the regular profile; use a separate browser profile for automatic page reading.
- **Voice input:** allow microphone access in Windows Privacy settings. The Whisper `base` model downloads on first use and needs internet for that download.
- **Desktop actions:** keep the target app in the foreground and use a screenshot before requesting coordinate actions.
- **Import/startup error:** run `Launch Miku.bat` from the project folder to keep its console output visible.
