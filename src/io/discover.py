"""
src/io/discover.py
==================
Generic raw file discovery based on configuration.

Supported discovery modes:
- hs6_folders: raw_root/<HS6>/*.csv
- flat:        raw_root/*.csv

This keeps the software general-purpose and data-agnostic.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable

HS6_DIR_RE = re.compile(r"^\d{6}$")


def list_hs6_folders(raw_root: Path) -> list[Path]:
    """List subfolders that look like HS6 codes (six digits)."""
    if not raw_root.exists():
        return []
    out = []
    for p in raw_root.iterdir():
        if p.is_dir() and HS6_DIR_RE.match(p.name):
            out.append(p)
    return sorted(out)


def discover_files_hs6_folders(raw_root: Path, glob_pattern: str, allowed_hs6: Iterable[str] | None) -> list[Path]:
    """
    Discover CSV files in raw_root/<HS6>/ matching glob_pattern.
    If allowed_hs6 is provided, restrict to those HS6 folders only.
    """
    folders = list_hs6_folders(raw_root)
    if allowed_hs6 is not None:
        allowed = set(str(x).zfill(6) for x in allowed_hs6)
        folders = [f for f in folders if f.name in allowed]

    files: list[Path] = []
    for f in folders:
        files.extend(sorted([p for p in f.glob(glob_pattern) if p.is_file()]))

    return sorted(files)


def discover_files_flat(raw_root: Path, glob_pattern: str) -> list[Path]:
    """Discover CSV files directly under raw_root/ matching glob_pattern."""
    if not raw_root.exists():
        return []
    return sorted([p for p in raw_root.glob(glob_pattern) if p.is_file()])


def discover_raw_files(
    raw_root: Path,
    discovery_mode: str,
    glob_pattern: str = "*.csv",
    allowed_hs6: Iterable[str] | None = None,
) -> list[Path]:
    """
    Unified discovery function.

    Parameters
    ----------
    raw_root : Path
        Root directory for raw files.
    discovery_mode : str
        "hs6_folders" or "flat"
    glob_pattern : str
        Typically "*.csv"
    allowed_hs6 : iterable[str] | None
        Restrict to these HS6 folders (only applies to hs6_folders mode).

    Returns
    -------
    list[Path]
        File paths in deterministic order.
    """
    mode = discovery_mode.strip().lower()

    if mode == "hs6_folders":
        return discover_files_hs6_folders(raw_root, glob_pattern, allowed_hs6=allowed_hs6)

    if mode == "flat":
        return discover_files_flat(raw_root, glob_pattern)

    raise ValueError(f"Unknown discovery_mode: {discovery_mode}. Use 'hs6_folders' or 'flat'.")