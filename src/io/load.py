"""
src/io/load.py
==============
Generic loader for raw CSV files discovered by src/io/discover.py.

Features:
- Reads a provided list of file paths (already discovered)
- Supports configurable separator (sep)
- Supports encoding + fallback encodings
- Attaches provenance columns:
  - _source_file
  - _source_path
  - _source_hs6_folder
  - _source_encoding (which encoding succeeded)
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.utils.logging import get_logger

log = get_logger(__name__)


def _read_csv_with_fallback(fp: Path, sep: str, encoding: str, fallbacks: list[str]) -> tuple[pd.DataFrame, str]:
    """
    Try reading a CSV with an encoding, then fallbacks if UnicodeDecodeError occurs.
    Returns (df, encoding_used).
    """
    encodings_to_try = [encoding] + [e for e in fallbacks if e != encoding]

    last_err = None
    for enc in encodings_to_try:
        try:
            df = pd.read_csv(fp, sep=sep, encoding=enc)
            return df, enc
        except UnicodeDecodeError as e:
            last_err = e
            continue

    # If everything failed, re-raise the last error (most informative)
    raise last_err


def load_csv_files(
    files: list[Path],
    sep: str = ",",
    encoding: str = "utf-8",
    encoding_fallbacks: list[str] | None = None,
) -> pd.DataFrame:
    if not files:
        raise FileNotFoundError("No input files provided to load_csv_files().")

    if encoding_fallbacks is None:
        encoding_fallbacks = ["utf-8-sig", "cp1252", "latin1"]

    dfs = []
    total = 0

    for fp in files:
        df, used_enc = _read_csv_with_fallback(fp, sep=sep, encoding=encoding, fallbacks=encoding_fallbacks)

        # provenance
        df["_source_file"] = fp.name
        df["_source_path"] = str(fp)
        parent = fp.parent.name
        df["_source_hs6_folder"] = parent if parent.isdigit() and len(parent) == 6 else None
        df["_source_encoding"] = used_enc

        # log encoding choice only when not default (to reduce noise)
        if used_enc != encoding:
            log.info(f"Encoding fallback used for {fp.name}: {used_enc}")

        dfs.append(df)
        total += len(df)

    out = pd.concat(dfs, ignore_index=True)
    log.info(f"Loaded {len(files)} files | Rows: {total:,} | Combined: {len(out):,}")
    return out