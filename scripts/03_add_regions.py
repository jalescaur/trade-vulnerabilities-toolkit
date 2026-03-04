"""
scripts/03_add_regions.py
=========================
Adds region columns and writes:
- new intermediate parquet with regions
- coverage audits to Excel for iteration

This remains a "constructor" step (data preparation), not substantive analysis.
"""
# --- bootstrap: ensure repo root is on PYTHONPATH ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.config import DATA_PROCESSED, COL_REPORTER, COL_PARTNER
from src.taxonomy.regions import add_regions, audit_region_coverage
from src.io.export import export_parquet, export_excel
from src.utils.logging import get_logger

log = get_logger(__name__)


def main() -> None:
    in_path = DATA_PROCESSED / "intermediate_tables" / "aiinfra_v01.parquet"
    out_parquet = DATA_PROCESSED / "intermediate_tables" / "aiinfra_v01_regions.parquet"
    out_dir = DATA_PROCESSED / "exploratory_excels"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        raise FileNotFoundError(
            f"Missing intermediate dataset: {in_path}\n"
            f"Run: python scripts/01_build_dataset.py"
        )

    df = pd.read_parquet(in_path)
    log.info(f"Loaded: {in_path} | rows={len(df):,}, cols={len(df.columns)}")

    # Add region fields
    df_r = add_regions(df)
    export_parquet(df_r, out_parquet, index=False)
    log.info(f"Wrote: {out_parquet}")

    # Coverage audits (export each to Excel)
    rep_cov = audit_region_coverage(df_r, col=COL_REPORTER, top_n=100)
    par_cov = audit_region_coverage(df_r, col=COL_PARTNER, top_n=100)

    export_excel(rep_cov, out_dir / "audit_region_coverage_reporter.xlsx", sheet_name="reporter", index=False)
    export_excel(par_cov, out_dir / "audit_region_coverage_partner.xlsx", sheet_name="partner", index=False)

    log.info("Region coverage audits exported ✅")
    log.info("Next: open the audit xlsx files and add missing ISO3 codes to REGION_MAP for full coverage.")


if __name__ == "__main__":
    main()