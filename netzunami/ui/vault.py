import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
import base64
import hashlib


class Vault:
    def __init__(self, vault_path: str | None = None):
        if vault_path is None:
            vault_path = str(Path.home() / ".netzunami" / "vault.enc")
        self.path = vault_path
        self._key = None
        self._data: dict = {}

    def _derive_key(self, master_pass: str) -> bytes:
        return base64.urlsafe_b64encode(
            hashlib.sha256(master_pass.encode()).digest()
        )

    def unlock(self, master_pass: str):
        self._key = self._derive_key(master_pass)
        if os.path.exists(self.path):
            try:
                with open(self.path, "rb") as f:
                    encrypted = f.read()
                fernet = Fernet(self._key)
                decrypted = fernet.decrypt(encrypted)
                self._data = json.loads(decrypted)
            except Exception:
                self._data = {}
        else:
            self._data = {}

    def lock(self):
        self._key = None

    def save(self):
        if self._key is None:
            raise RuntimeError("Vault locked")
        fernet = Fernet(self._key)
        encrypted = fernet.encrypt(json.dumps(self._data, indent=2).encode())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "wb") as f:
            f.write(encrypted)

    def get(self, host: str, user: str = "") -> str | None:
        for entry in self._data.get("credentials", []):
            if entry.get("host") == host and (not user or entry.get("user") == user):
                return entry.get("password")
        return None

    def set(self, host: str, user: str, password: str):
        creds = self._data.setdefault("credentials", [])
        for entry in creds:
            if entry["host"] == host and entry["user"] == user:
                entry["password"] = password
                self.save()
                return
        creds.append({"host": host, "user": user, "password": password})
        self.save()

    def list_sessions(self) -> list[dict]:
        return self._data.get("credentials", [])

    def delete(self, host: str, user: str):
        creds = self._data.get("credentials", [])
        self._data["credentials"] = [
            c for c in creds if not (c["host"] == host and c["user"] == user)
        ]
        self.save()
