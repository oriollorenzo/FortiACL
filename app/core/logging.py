import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import settings


def setup_logging(log_file: str | None = None) -> None:
    root = logging.getLogger()

    if getattr(root, "_forti_logging_configured", False):
        return

    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(log_file) if log_file else log_dir / "app.log"

    formatter = logging.Formatter(
        "%(asctime)s %(process)d %(levelname)s [%(name)s] %(message)s"
    )

    root.setLevel(logging.INFO)

    if root.handlers:
        root.handlers.clear()

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    root._forti_logging_configured = True
