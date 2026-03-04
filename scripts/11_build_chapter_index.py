"""
scripts/11_build_chapter_index.py
=================================
Build an index/catalog of chapter tables in outputs/tables/.

Usage:
  python scripts/11_build_chapter_index.py

Output:
  outputs/tables/Table_Index.xlsx

This file helps manuscript writing:
- quickly locate each table
- keeps a stable numbering convention
"""

from __future__ import annotations

from pathlib import Path
import re
import pandas as pd

from src.io.excel_format import write_excel_table
from src.utils.logging import get_logger

log = get_logger(__name__)


TABLES_DIR = Path("outputs") / "tables"
PAT = re.compile(r"^Table_(\d{2})_(.+)\.xlsx$", re.IGNORECASE)


def main() -> None:
    if not TABLES_DIR.exists():
        raise FileNotFoundError(f"Missing tables directory: {TABLES_DIR}. Run scripts/10_build_metrics_tables.py first.")

    rows = []
    for p in sorted(TABLES_DIR.glob("Table_*.xlsx")):
        m = PAT.match(p.name)
        if m:
            num = int(m.group(1))
            key = m.group(2).replace("_", " ")
        else:
            num = None
            key = p.stem.replace("_", " ")

        rows.append({
            "Table_No": num,
            "File": p.name,
            "Title_Key": key,
            "Path": str(p.resolve()),
        })

    df = pd.DataFrame(rows).sort_values(["Table_No", "File"], na_position="last")

    out = TABLES_DIR / "Table_Index.xlsx"
    write_excel_table(
        df,
        out,
        sheet_name="Index",
        title="Chapter Table Index (auto-generated)",
        note="This index is auto-generated from files in outputs/tables/. "
             "Table_No is parsed from filename pattern Table_XX_*.xlsx.",
        int_cols=["Table_No"],
        freeze_at="A3",
    )

    log.info(f"Wrote: {out.resolve()}")
    log.info("Done ✅")


if __name__ == "__main__":
    main()