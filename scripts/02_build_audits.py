"""
scripts/02_build_audits.py
==========================
Config-driven audits from the intermediate dataset.

Usage:
  python scripts/02_build_audits.py --config configs/default.yaml

Input:
- data/processed/intermediate_tables/<intermediate_dataset_name>

Outputs (exploratory; regenerated):
- data/processed/exploratory_excels/audit_*.xlsx

These audits document dataset integrity and cleaning decisions.
"""

from __future__ import annotations

import argparse
import pandas as pd

from src.runtime_config import load_config, cfg_paths
from src.io.export import export_excel
from src.io.validate import (
    audit_missingness,
    audit_duplicates,
    audit_iso3_codes,
    audit_year_coverage,
    audit_year_hs6_coverage,
    audit_flow_distribution,
    audit_aggregate_flags,
)
from src.utils.logging import get_logger

log = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, help="Path to YAML config.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    in_path = paths["intermediate_dataset"]
    out_dir = paths["exploratory_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        raise FileNotFoundError(
            f"Intermediate dataset not found: {in_path}\n"
            f"Run: python scripts/01_build_dataset.py --config {args.config}"
        )

    df = pd.read_parquet(in_path)
    log.info(f"Loaded intermediate: {in_path} | rows={len(df):,}, cols={len(df.columns)}")

    # 1) Missingness (canonical + optional fields)
    required_cols = cfg["schema"]["required_columns"]
    optional_cols = ["flow", "reporter_name_raw", "partner_name_raw"]
    cols = list(dict.fromkeys(required_cols + optional_cols))  # preserve order, remove duplicates
    miss = audit_missingness(df, cols=cols)
    export_excel(miss.details, out_dir / "audit_missingness.xlsx", sheet_name="missingness", index=False)

    # 2) ISO3 anomalies
    iso = audit_iso3_codes(df, cols=("reporter", "partner"), top_n=100)
    export_excel(iso.details, out_dir / "audit_iso3_codes.xlsx", sheet_name="iso3", index=False)

    # 3) Duplicates (key = year + reporter + partner + hs6 + flow)
    dup_key = ["year", "reporter", "partner", "hs6", "flow"]
    dups = audit_duplicates(df, subset=dup_key)
    export_excel(dups.details, out_dir / "audit_duplicates.xlsx", sheet_name="duplicates", index=False)

    # 4) Coverage by year
    yc = audit_year_coverage(df)
    export_excel(yc.details, out_dir / "audit_year_coverage.xlsx", sheet_name="year", index=False)

    # 5) Coverage by year x HS6
    yh = audit_year_hs6_coverage(df)
    export_excel(yh.details, out_dir / "audit_year_hs6_coverage.xlsx", sheet_name="year_hs6", index=False)

    # 6) Flow distribution
    fd = audit_flow_distribution(df)
    export_excel(fd.details, out_dir / "audit_flow_distribution.xlsx", sheet_name="flows", index=False)

    # 7) Aggregate flags (if present)
    ag = audit_aggregate_flags(df)
    export_excel(ag.details, out_dir / "audit_aggregate_flags.xlsx", sheet_name="aggregates", index=False)

    log.info("Audits complete ✅")


if __name__ == "__main__":
    main()