from __future__ import annotations

import logging

from .config import LOG_PATH, ensure_directories


def setup_logging() -> logging.Logger:
    ensure_directories()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return logging.getLogger("jarvis_assistant")
