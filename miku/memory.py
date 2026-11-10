import sqlite3
from contextlib import contextmanager
from .config import DB_PATH

@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, role TEXT, content TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        db.execute("CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY, content TEXT UNIQUE, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally: db.close()

def remember(role, content):
    with connect() as db:
        db.execute("INSERT INTO messages(role,content) VALUES(?,?)", (role, content))

def history(limit=30):
    with connect() as db:
        return [{"role": r, "content": c} for r,c in db.execute("SELECT role,content FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()[::-1]]

def add_memory(content):
    with connect() as db: db.execute("INSERT OR IGNORE INTO memories(content) VALUES(?)", (content,))

def search_memory(query):
    with connect() as db: return [r[0] for r in db.execute("SELECT content FROM memories WHERE content LIKE ? ORDER BY id DESC LIMIT 10", (f"%{query}%",))]

def clear_history():
    with connect() as db: db.execute("DELETE FROM messages")

def delete_memory(query):
    with connect() as db:
        cur=db.execute("DELETE FROM memories WHERE content LIKE ?", (f"%{query}%",))
        return cur.rowcount
