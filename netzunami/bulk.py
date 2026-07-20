"""Bulk operations: mass backup, template apply, diff"""

import os
import re
import json
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .connector import ssh_connect, run_commands
from .config import Config


def read_hosts(hosts_file: str) -> list[dict]:
    hosts = []
    with open(hosts_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            host = parts[0].strip()
            user = parts[1].strip() if len(parts) > 1 else "admin"
            port = int(parts[2].strip()) if len(parts) > 2 else 22
            hosts.append({"host": host, "user": user, "port": port})
    return hosts


def backup(hosts: list[dict], output_dir: str | None = None, max_workers: int = 5):
    if output_dir is None:
        output_dir = str(Path.home() / ".netzunami" / "backups")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    results = []

    def _backup_one(entry: dict):
        try:
            client = ssh_connect(entry["host"], entry["user"], port=entry["port"])
            raw = run_commands(client, ["show running-config"])
            client.close()

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"{entry['host']}_{ts}.cfg"
            fpath = out / fname
            with open(fpath, "w") as f:
                f.write(raw)
            return {"host": entry["host"], "status": "ok", "file": str(fpath)}
        except Exception as e:
            return {"host": entry["host"], "status": "error", "error": str(e)}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_backup_one, e): e for e in hosts}
        for f in as_completed(futures):
            results.append(f.result())

    return results


def apply_template(
    host: str,
    user: str,
    template: str,
    port: int = 22,
    password: str = "",
    vendor: str = "cisco",
) -> dict:
    try:
        client = ssh_connect(host, user, port=port, password=password or None)
        commands = [line.strip() for line in template.splitlines()
                   if line.strip() and not line.strip().startswith("#")]
        output = run_commands(client, commands, vendor=vendor)
        client.close()
        return {"host": host, "status": "ok", "output": output[:500]}
    except Exception as e:
        return {"host": host, "status": "error", "error": str(e)}


def bulk_apply(
    hosts: list[dict],
    template: str,
    passwords: dict[str, str] | None = None,
    max_workers: int = 5,
    confirm: bool = True,
) -> list[dict]:
    results = []
    passwords = passwords or {}

    def _apply(entry: dict):
        pw = passwords.get(entry["host"], "")
        return apply_template(entry["host"], entry["user"], template, entry["port"], pw)

    if confirm:
        print(f"\n  Hosts: {len(hosts)}")
        print(f"  Comandi:\n{template}\n")
        resp = input("  Confermi push? [y/N]: ")
        if resp.lower() != "y":
            return [{"host": e["host"], "status": "cancelled"} for e in hosts]

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_apply, e): e for e in hosts}
        for f in as_completed(futures):
            results.append(f.result())

    return results


def render_template(template: str, variables: dict[str, str]) -> str:
    for key, val in variables.items():
        template = template.replace(f"{{{{{key}}}}}", val)
    return template
