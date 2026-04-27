from collections import deque
from pathlib import Path
import re


LOG_DIR = Path("logs")
LOG_BASENAME = "app.log"


def _log_sort_key(path: Path) -> tuple[int, int]:
    name = path.name

    if name == LOG_BASENAME:
        return (1, 0)

    m = re.fullmatch(r"app\.log\.(\d+)", name)
    if m:
        return (0, int(m.group(1)))

    return (2, 0)


def _iter_log_files() -> list[Path]:
    if not LOG_DIR.exists():
        return []

    files = [
        p for p in LOG_DIR.iterdir()
        if p.is_file()
        and p.name.startswith(LOG_BASENAME)
        and not p.name.endswith(".gz")
    ]

    files.sort(key=_log_sort_key, reverse=True)
    return files


def tail_log(lines: int = 200, query: str | None = None) -> list[str]:
    log_files = _iter_log_files()
    if not log_files:
        return []

    buffer = deque(maxlen=lines * 5 if query else lines)

    for log_file in log_files:
        try:
            with log_file.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    buffer.append(line.rstrip("\n"))
        except FileNotFoundError:
            continue

    data = list(buffer)

    if query:
        q = query.lower()
        data = [line for line in data if q in line.lower()]
        if len(data) > lines:
            data = data[-lines:]

    return data
