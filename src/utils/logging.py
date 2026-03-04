"""
src/utils/logging.py
====================
Standard project logger (console + file).

Why:
- Keeps a reproducible record of what happened in each pipeline run.
- Writes to outputs/logs by default (config scripts also ensure this folder exists).

This module MUST provide:
- get_logger(name, log_dir=None, level=logging.INFO) -> logging.Logger
"""

from __future__ import annotations

import logging
from pathlib import Path
from datetime import datetime


def get_logger(
    name: str,
    log_dir: Path | None = None,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Create or return a configured logger that logs to:
    - console (StreamHandler)
    - file (FileHandler) with timestamped filename

    Idempotent: if the logger already has handlers, returns it as-is.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # If already configured, return it
    if logger.handlers:
        return logger

    if log_dir is None:
        log_dir = Path("outputs") / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = log_dir / f"{ts}.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # File handler
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logger.info(f"Logger initialized. Writing to: {logfile}")
    return logger