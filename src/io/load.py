"""
src/io/load.py
==============
Generic loader for raw CSV files.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.utils.logging import get_logger

log = get_logger(__name__)


def _read_csv_with_fallback(fp: Path, sep: str, encoding: str, fallbacks: list[str]) -> tuple[pd.DataFrame, str]:
    """
    Try reading a CSV with an encoding, then fallbacks.
    Forces index_col=False to prevent column shifting issues.
    """
    encodings_to_try = [encoding] + [e for e in fallbacks if e != encoding]

    last_err = None
    for enc in encodings_to_try:
        try:
            # FIX: index_col=False is crucial for some Comtrade CSVs to avoid
            # treating the first column (typeCode) as an index, which shifts everything.
            df = pd.read_csv(fp, sep=sep, encoding=enc, index_col=False)
            return df, enc
        except UnicodeDecodeError as e:
            last_err = e
            continue
        except pd.errors.ParserError:
            # If standard parse fails, try looser engine (slower but robust)
            try:
                df = pd.read_csv(fp, sep=sep, encoding=enc, index_col=False, engine="python")
                return df, enc
            except Exception as e:
                last_err = e
                continue

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

        # clean column names (strip whitespace)
        df.columns = df.columns.astype(str).str.strip()

        dfs.append(df)
        total += len(df)
        if len(dfs) % 10 == 0:
            log.info(f"Loaded {len(dfs)}/{len(files)} files...")

    log.info(f"Loaded {len(files)} files | Rows: {total:,}")

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)
    log.info(f"Combined: {len(combined):,} rows")
    return combined