"""
scripts/print_config_summary.py
===============================
Generate a clean Excel summary of the runtime configuration.

Why:
- Makes the pipeline more transparent and easier to cite in a manuscript.
- Produces a "receipt" of:
  - discovery settings
  - basket HS6 list (and optional metadata)
  - schema mapping (rename_map)
  - filter policy (years, positive values)
  - outputs settings

Usage:
  python scripts/print_config_summary.py --config configs/default.yaml

Output:
  data/processed/exploratory_excels/config_summary.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.runtime_config import load_config, cfg_paths
from src.io.export import export_excel
from src.utils.logging import get_logger

log = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, help="Path to YAML config.")
    return p.parse_args()


def basket_table(cfg: dict) -> pd.DataFrame:
    hs6 = [str(x).zfill(6) for x in cfg["basket"]["hs6"]]
    meta = cfg["basket"].get("meta", {})

    rows = []
    for code in hs6:
        m = meta.get(code, {})
        rows.append({
            "hs6": code,
            "desc": m.get("desc", ""),
            "layer": m.get("layer", ""),
            "proxy": bool(m.get("proxy", False)),
        })
    return pd.DataFrame(rows).sort_values("hs6")


def schema_table(cfg: dict) -> pd.DataFrame:
    rm = cfg["schema"]["rename_map"]
    rows = [{"raw_column": k, "canonical_column": v} for k, v in rm.items()]
    return pd.DataFrame(rows).sort_values(["canonical_column", "raw_column"])


def settings_table(cfg: dict) -> pd.DataFrame:
    proj = cfg.get("project", {})
    inputs = cfg.get("inputs", {})
    filters = cfg.get("filters", {})
    outputs = cfg.get("outputs", {})

    rows = [
        ("project.name", proj.get("name", "")),
        ("project.basket_name", proj.get("basket_name", "")),
        ("project.basket_version", proj.get("basket_version", "")),
        ("project.description", proj.get("description", "")),
        ("inputs.raw_root", inputs.get("raw_root", "")),
        ("inputs.discovery_mode", inputs.get("discovery_mode", "")),
        ("inputs.csv_sep", inputs.get("csv_sep", "")),
        ("inputs.glob", inputs.get("glob", "")),
        ("filters.year_min", filters.get("year_min", "")),
        ("filters.year_max", filters.get("year_max", "")),
        ("filters.value_positive_only", filters.get("value_positive_only", "")),
        ("outputs.processed_root", outputs.get("processed_root", "")),
        ("outputs.intermediate_dataset_name", outputs.get("intermediate_dataset_name", "")),
        ("outputs.exploratory_excels_dir", outputs.get("exploratory_excels_dir", "")),
        ("outputs.logs_dir", outputs.get("logs_dir", "")),
    ]
    return pd.DataFrame(rows, columns=["key", "value"])


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    out_dir = paths["exploratory_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "config_summary.xlsx"

    # Build tables
    t_settings = settings_table(cfg)
    t_basket = basket_table(cfg)
    t_schema = schema_table(cfg)

    # Write a single workbook with multiple sheets
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        t_settings.to_excel(writer, sheet_name="settings", index=False)
        t_basket.to_excel(writer, sheet_name="basket", index=False)
        t_schema.to_excel(writer, sheet_name="schema_rename_map", index=False)

    log.info(f"Wrote config summary: {out_path}")
    log.info("Done ✅")


if __name__ == "__main__":
    main()