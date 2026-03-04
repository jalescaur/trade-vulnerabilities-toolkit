"""
scripts/04_add_country_names.py
===============================
Config-driven country name enrichment.

Usage:
  python scripts/04_add_country_names.py --config configs/default.yaml

Input:
- data/processed/intermediate_tables/<intermediate_dataset_name>

Outputs:
- data/processed/intermediate_tables/dataset_country_names.parquet
- data/processed/exploratory_excels/audit_country_name_coverage.xlsx

This step improves manuscript readiness by adding English full names.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from src.runtime_config import load_config, cfg_paths
from src.io.export import export_parquet, export_excel
from src.taxonomy.countries import add_country_names, audit_country_name_coverage
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
    log.info(f"Loaded: {in_path} | rows={len(df):,}, cols={len(df.columns)}")

    df2 = add_country_names(df)

    # Output name derived from intermediate name
    base = Path(cfg["outputs"]["intermediate_dataset_name"]).stem
    out_path = paths["processed_root"] / "intermediate_tables" / f"{base}_country_names.parquet"

    export_parquet(df2, out_path, index=False)
    log.info(f"Wrote: {out_path}")

    audit = audit_country_name_coverage(df2)
    export_excel(audit, out_dir / "audit_country_name_coverage.xlsx", sheet_name="coverage", index=False)
    log.info("Exported: audit_country_name_coverage.xlsx ✅")

    log.info("Done ✅")


if __name__ == "__main__":
    main()