"""
src/io/load.py
==============
Generic loader for raw CSV files discovered by src/io/discover.py.

Key features:
- Reads a provided list of file paths (already discovered)
- Supports configurable CSV separator (sep)
- Attaches provenance columns for traceability:
  - _source_file
  - _source_path
  - _source_hs6_folder (if file is inside an HS6 folder)
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.utils.logging import get_logger

log = get_logger(__name__)


def load_csv_files(files: list[Path], sep: str = ",") -> pd.DataFrame:
    if not files:
        raise FileNotFoundError("No input files provided to load_csv_files().")

    dfs = []
    total = 0

    for fp in files:
        df = pd.read_csv(fp, sep=sep)
        df["_source_file"] = fp.name
        df["_source_path"] = str(fp)

        # If files are stored under raw_root/<HS6>/..., parent folder is HS6
        parent = fp.parent.name
        df["_source_hs6_folder"] = parent if parent.isdigit() and len(parent) == 6 else None

        dfs.append(df)
        total += len(df)

    out = pd.concat(dfs, ignore_index=True)
    log.info(f"Loaded {len(files)} files | Rows: {total:,} | Combined: {len(out):,}")
    return out