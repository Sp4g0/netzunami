import time
import re
from pathlib import Path
from .models import Finding
from .analyzer import COMMON_ISSUES


def listen_session(
    log_path: str,
    vendor: str = "cisco",
    interval: float = 1.0,
    callback=None,
):
    rules = COMMON_ISSUES.get(vendor, [])
    path = Path(log_path)
    last_size = path.stat().st_size if path.exists() else 0
    seen_lines = set()

    print(f"  Listening: {log_path}")

    while True:
        if not path.exists():
            time.sleep(interval)
            continue

        current_size = path.stat().st_size
        if current_size <= last_size:
            time.sleep(interval)
            continue

        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(last_size)
            new_data = f.read()

        for line in new_data.splitlines():
            line_stripped = line.strip()
            if not line_stripped or line_stripped in seen_lines:
                continue
            seen_lines.add(line_stripped)

            for rule in rules:
                if re.search(rule["pattern"], line_stripped, re.IGNORECASE):
                    finding = Finding(
                        severity=rule["severity"],
                        title=rule["title"],
                        detail=rule["detail"],
                        suggestion=rule["suggestion"],
                    )
                    if callback:
                        callback(finding, line_stripped)
                    else:
                        sev = rule["severity"].value
                        print(f"  [{sev}] {rule['title']}")
                        if rule["suggestion"]:
                            print(f"         → {rule['suggestion']}")

        last_size = current_size
        time.sleep(interval)
