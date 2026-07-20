import json
import os
from pathlib import Path


SESSION_FILE = str(Path.home() / ".netzunami" / "sessions.json")


def load_sessions() -> list[dict]:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE) as f:
            return json.load(f)
    return []


def save_sessions(sessions: list[dict]):
    Path(SESSION_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


def add_session(name: str, host: str, user: str, port: int = 22, vendor: str = "cisco"):
    sessions = load_sessions()
    sessions.append({
        "name": name,
        "host": host,
        "user": user,
        "port": port,
        "vendor": vendor,
    })
    save_sessions(sessions)


def remove_session(host: str):
    sessions = load_sessions()
    sessions = [s for s in sessions if s["host"] != host]
    save_sessions(sessions)
