"""
scripts/01_build_dataset.py
===========================
Config-driven dataset builder.
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

    (processed_root / "intermediate_tables").mkdir(parents=True, exist_ok=True)
    exploratory_dir.mkdir(parents=True, exist_ok=True)

    mode = cfg["inputs"]["discovery_mode"]
    glob_pattern = cfg["inputs"]["glob"]
    allowed_hs6 = cfg["basket"]["hs6"]
    sep = cfg["inputs"]["csv_sep"]

    files = discover_raw_files(raw_root, discovery_mode=mode, glob_pattern=glob_pattern, allowed_hs6=allowed_hs6)
    if not files:
        raise FileNotFoundError("No raw files discovered. Check config and data/raw layout.")

    log.info(f"Discovered {len(files)} raw files.")

    enc = cfg["inputs"].get("csv_encoding", "utf-8")
    enc_fb = cfg["inputs"].get("csv_encoding_fallbacks", ["utf-8-sig", "cp1252", "latin1"])

    df_raw = load_csv_files(files, sep=sep, encoding=enc, encoding_fallbacks=enc_fb)

    if mode == "hs6_folders":
        if "_source_hs6_folder" not in df_raw.columns:
            raise RuntimeError("Expected _source_hs6_folder in df_raw.")

    if "cmdCode" not in df_raw.columns:
        df_raw["cmdCode"] = df_raw["_source_hs6_folder"]
    else:
        df_raw["cmdCode"] = df_raw["cmdCode"].fillna(df_raw["_source_hs6_folder"])

    df_raw["cmdCode"] = df_raw["cmdCode"].astype(str).str.strip()
    log.info(f"Raw loaded: rows={len(df_raw):,}, cols={len(df_raw.columns)}")

    basket_df = build_basket_df(cfg)
    log.info(f"Basket built: {len(basket_df)} HS6 codes")

    rename_map = dict(cfg["schema"]["rename_map"]) 
    required_columns = cfg["schema"]["required_columns"]

    if mode == "hs6_folders":
        rename_map["_source_hs6_folder"] = "hs6"
        if "cmdCode" in rename_map and rename_map["cmdCode"] == "hs6":
            rename_map["cmdCode"] = "cmdCode_raw"
        if "hs6" not in required_columns:
            required_columns = list(required_columns) + ["hs6"]

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

    export_parquet(df_norm, intermediate_path, index=False)
    log.info(f"Wrote intermediate parquet: {intermediate_path}")

    audit_xlsx = exploratory_dir / "audit_classification_versions.xlsx"
    export_excel(audit_cl, audit_xlsx, sheet_name="classification", index=False)
    export_csv(audit_cl, exploratory_dir / "audit_classification_versions.csv", index=False)

    # --- ADVANCED METADATA RECEIPT ---
    unique_reporters = df_norm["reporter"].nunique() if "reporter" in df_norm.columns else 0
    unique_partners = df_norm["partner"].nunique() if "partner" in df_norm.columns else 0
    total_value = df_norm["value"].sum() if "value" in df_norm.columns else 0

    receipt_data = {
        "Config File": str(Path(args.config).resolve()),
        "Raw Source Root": str(raw_root),
        "Discovery Mode": mode,
        "Files Loaded": int(len(files)),
        "Rows (Raw Combined)": int(len(df_raw)),
        "Rows (After Cleaning & Filters)": int(len(df_norm)),
        "Unique Reporter Countries": unique_reporters,
        "Unique Partner Countries": unique_partners,
        "Total Trade Value (USD)": float(total_value),
        "HS6 Codes in Basket": int(len(basket_df)),
        "Year Minimum": year_min,
        "Year Maximum": year_max,
    }

    # Calcula valor total por ano para o recibo
    if "year" in df_norm.columns and "value" in df_norm.columns:
        yearly_totals = df_norm.groupby("year")["value"].sum().to_dict()
        for y, val in sorted(yearly_totals.items()):
            receipt_data[f"Total Trade USD ({int(y)})"] = float(val)

    # Transforma em uma tabela vertical (Chave - Valor) para melhor leitura
    receipt_df = pd.DataFrame(list(receipt_data.items()), columns=["Metadata Metric", "Value"])

    receipt_xlsx = exploratory_dir / "build_receipt.xlsx"
    export_excel(receipt_df, receipt_xlsx, sheet_name="receipt", index=False)
    log.info(f"Wrote advanced build receipt: {receipt_xlsx}")

    log.info("Build complete ✅")

if __name__ == "__main__":
    main()