# Security

Inference uses the local Ollama endpoint; there is no cloud fallback. File tools are limited to Documents, Desktop, Downloads, and this project. Text reads are capped at 1 MB. There is no shell execution, file deletion, email, credentials, or administrator tool. File overwrites preserve a timestamped backup. Memory can be deleted only through an explicit Miku request.

The Ctrl+J listener is a per-user process started from the Windows Startup folder. It registers one hotkey and starts or focuses Miku. It does not install a service or request elevation.

Desktop clicks and typing can affect the focused app. High-impact approval uses a keyword heuristic, so it is not a complete safeguard. Miku has no form-submit tool, but review websites before sending or submitting anything. Webpage text is untrusted. Never ask Miku to handle credentials.

Chat and memory remain in `data/miku.sqlite3`. Push-to-talk records six seconds in memory and transcribes locally after the model is available; Miku does not intentionally save audio. Google searches open in the user's Chrome profile named Mikasa and send the search query to Google. Existing signed-in sessions in that profile may be active; Miku does not read credential stores or passwords. Chrome protects its regular profile from Playwright automation, so Miku opens pages for the user to review but cannot automatically extract page contents from this profile. If Google requests human verification, complete it manually; Miku will not solve or bypass it.
