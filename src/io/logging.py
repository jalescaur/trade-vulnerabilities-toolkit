"""
src/utils/logging.py
====================
Project logger (console + file).

Why:
- Reproducible research benefits from transparent records of:
  - which files were used
  - how many rows were filtered/dropped
  - detected classification versions / missingness / duplicates, etc.

Implementation:
- Uses Python's standard library `logging` (stable, ubiquitous).
- Writes to outputs/logs/ by default (configurable).

How to use:
    from src.utils.logging import get_logger
    log = get_logger(__name__)
    log.info("Hello")
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
    Create (or return existing) logger with:
    - StreamHandler (console)
    - FileHandler (timestamped log file)

    Parameters
    ----------
    name : str
        Usually __name__ from the caller.
    log_dir : Path | None
        Where to write log files. If None, uses ./outputs/logs relative to repo.
        (Caller can pass src.config.LOGS_DIR to keep consistent.)
    level : int
        Logging level.

    Notes
    -----
    - The function is idempotent: if handlers already exist, it won't duplicate them.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # prevent double logging in some contexts

    if logger.handlers:
        return logger  # already configured

    # Default location if none provided:
    if log_dir is None:
        log_dir = Path("outputs") / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    logfile = log_dir / f"{ts}.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console
    sh = logging.StreamHandler()
    sh.setLevel(level)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # File
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logger.info(f"Logger initialized. Writing to: {logfile}")
    return logger