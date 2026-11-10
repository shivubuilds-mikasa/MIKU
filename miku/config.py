from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
DB_PATH = DATA / "miku.sqlite3"
OLLAMA_URL = os.getenv("MIKU_OLLAMA_URL", os.getenv("JARVIS_OLLAMA_URL", "http://localhost:11434"))
DEFAULT_MODEL = os.getenv("MIKU_MODEL", os.getenv("JARVIS_MODEL", "qwen2.5:7b"))
MODELS = ["qwen3.5:2b", "qwen2.5:7b", "R4C3R/qwen2.5-coder-7b-instruct-heretic:q4_k_m"]
ALLOWED_ROOTS = [Path.home() / "Documents", Path.home() / "Desktop", Path.home() / "Downloads", ROOT]
