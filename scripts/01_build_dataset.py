"""
scripts/01_build_dataset.py
===========================
Config-driven dataset builder.

Usage:
  python scripts/01_build_dataset.py --config configs/default.yaml

Outputs:
- Intermediate parquet: data/processed/intermediate_tables/<intermediate_dataset_name>
- Exploratory audit Excel: data/processed/exploratory_excels/audit_classification_versions.xlsx
- Build receipt Excel: data/processed/exploratory_excels/build_receipt.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

from src.runtime_config import load_config, cfg_paths
from src.io.discover import discover_raw_files
from src.io.load import load_csv_files
from src.io.normalize import normalize_pipeline
from src.io.export import export_parquet, export_excel, export_csv
from src.utils.logging import get_logger

log = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, help="Path to YAML config.")
    return p.parse_args()


def build_basket_df(cfg: dict) -> pd.DataFrame:
    """
    Build basket DataFrame from config.

    Required:
      basket.hs6 list

    Optional:
      basket.meta dict with keys per HS6:
        desc, layer, proxy, etc.
    """
    hs6_list = [str(x).zfill(6) for x in cfg["basket"]["hs6"]]
    meta = cfg["basket"].get("meta", {})

    rows = []
    for code in hs6_list:
        m = meta.get(code, {})
        rows.append({
            "hs6": code,
            "desc": m.get("desc", ""),
            "layer": m.get("layer", ""),
            "proxy": bool(m.get("proxy", False)),
            "basket_name": cfg.get("project", {}).get("basket_name", ""),
            "basket_version": cfg.get("project", {}).get("basket_version", ""),
        })
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    raw_root = paths["raw_root"]
    processed_root = paths["processed_root"]
    exploratory_dir = paths["exploratory_dir"]
    intermediate_path = paths["intermediate_dataset"]

    # Ensure directories exist
    (processed_root / "intermediate_tables").mkdir(parents=True, exist_ok=True)
    exploratory_dir.mkdir(parents=True, exist_ok=True)

    # Discover raw files
    mode = cfg["inputs"]["discovery_mode"]
    glob_pattern = cfg["inputs"]["glob"]
    allowed_hs6 = cfg["basket"]["hs6"]
    sep = cfg["inputs"]["csv_sep"]

    files = discover_raw_files(raw_root, discovery_mode=mode, glob_pattern=glob_pattern, allowed_hs6=allowed_hs6)
    if not files:
        raise FileNotFoundError(
            f"No raw files discovered under {raw_root} using mode={mode} glob={glob_pattern}.\n"
            f"Check config and data/raw layout."
        )

    log.info(f"Discovered {len(files)} raw files.")

    # Load
    sep = cfg["inputs"]["csv_sep"]
    enc = cfg["inputs"].get("csv_encoding", "utf-8")
    enc_fb = cfg["inputs"].get("csv_encoding_fallbacks", ["utf-8-sig", "cp1252", "latin1"])

    df_raw = load_csv_files(files, sep=sep, encoding=enc, encoding_fallbacks=enc_fb)
    log.info(f"Raw loaded: rows={len(df_raw):,}, cols={len(df_raw.columns)}")

    # Build basket
    basket_df = build_basket_df(cfg)
    log.info(f"Basket built: {len(basket_df)} HS6 codes")

    # Normalize (config-driven)
    rename_map = cfg["schema"]["rename_map"]
    required_columns = cfg["schema"]["required_columns"]

    year_min = cfg["filters"].get("year_min")
    year_max = cfg["filters"].get("year_max")
    value_positive_only = bool(cfg["filters"].get("value_positive_only", True))

    df_norm, audit_cl = normalize_pipeline(
        df_raw=df_raw,
        rename_map=rename_map,
        required_columns=required_columns,
        basket_df=basket_df,
        year_min=year_min,
        year_max=year_max,
        value_positive_only=value_positive_only,
    )

    # Export intermediate dataset
    export_parquet(df_norm, intermediate_path, index=False)
    log.info(f"Wrote intermediate parquet: {intermediate_path}")

    # Export classification audit (exploratory)
    audit_xlsx = exploratory_dir / "audit_classification_versions.xlsx"
    export_excel(audit_cl, audit_xlsx, sheet_name="classification", index=False)
    export_csv(audit_cl, exploratory_dir / "audit_classification_versions.csv", index=False)
    log.info(f"Wrote classification audit: {audit_xlsx}")

    # Receipt (what ran, on what)
    receipt = pd.DataFrame([{
        "config": str(Path(args.config).resolve()),
        "raw_root": str(raw_root),
        "discovery_mode": mode,
        "files_loaded": int(len(files)),
        "rows_raw_combined": int(len(df_raw)),
        "rows_after_normalization": int(len(df_norm)),
        "hs6_count": int(len(basket_df)),
        "hs6_codes": ", ".join(basket_df["hs6"].tolist()),
        "year_min": year_min,
        "year_max": year_max,
        "sep": sep,
    }])

    receipt_xlsx = exploratory_dir / "build_receipt.xlsx"
    export_excel(receipt, receipt_xlsx, sheet_name="receipt", index=False)
    log.info(f"Wrote build receipt: {receipt_xlsx}")

    log.info("Build complete ✅")


if __name__ == "__main__":
    main()