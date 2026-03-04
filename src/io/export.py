"""
src/io/export.py
================
Unified export helpers for the project.

Project policy (as you specified):
- Exploratory / intermediate tables -> data/processed/
- Final article/chapter tables -> outputs/tables/ (Excel)
- Figures -> outputs/figures/ (handled elsewhere)

Why centralize exports:
- Prevents notebooks/scripts from scattering ad-hoc file paths.
- Keeps the repo consistent and easier to reproduce.

No academic citations needed (engineering utility), but this supports transparent workflow.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd


def export_excel(
    df: pd.DataFrame,
    path: Path,
    sheet_name: str = "Sheet1",
    index: bool = False,
) -> Path:
    """
    Export a DataFrame to Excel (XLSX) using openpyxl engine.

    Notes:
    - Excel is ideal for chapter-ready tables because it is easily reviewed and edited.
    - For archival reproducibility, consider also exporting a CSV version of the same table.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=index)
    return path


def export_parquet(df: pd.DataFrame, path: Path, index: bool = False) -> Path:
    """
    Export DataFrame to Parquet.

    Why Parquet:
    - Efficient storage
    - Preserves dtypes better than CSV
    - Speeds up repeated analysis work

    This is appropriate for intermediate datasets in data/processed/.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=index)
    return path


def export_csv(df: pd.DataFrame, path: Path, index: bool = False) -> Path:
    """
    Export DataFrame to CSV (machine-readable companion to Excel tables).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)
    return path