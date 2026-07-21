import json
import os
from pathlib import Path

SESSION_FILE = str(Path.home() / ".netzunami" / "sessions.json")
LAST_SESSION_FILE = str(Path.home() / ".netzunami" / "last_session.json")


def load_sessions() -> list[dict]:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            return json.load(f)
    return []


def save_sessions(sessions: list[dict]):
    Path(SESSION_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


def add_session(name: str, host: str, user: str, port: int = 22):
    sessions = load_sessions()
    sessions.append({
        "name": name,
        "host": host,
        "user": user,
        "port": port,
    })
    save_sessions(sessions)


def remove_session(host: str):
    sessions = load_sessions()
    sessions = [s for s in sessions if s["host"] != host]
    save_sessions(sessions)


def save_last_session(user: str, port: int = 22):
    Path(LAST_SESSION_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(LAST_SESSION_FILE, "w") as f:
        json.dump({"user": user, "port": port}, f)


def load_last_session() -> dict:
    if os.path.exists(LAST_SESSION_FILE):
        with open(LAST_SESSION_FILE) as f:
            return json.load(f)
    return {"user": "admin", "port": 22}
