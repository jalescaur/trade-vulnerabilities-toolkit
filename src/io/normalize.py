"""
src/io/normalize.py
===================
Config-driven normalization with COLUMN DEBUGGING and Flow Consolidation.
"""

from __future__ import annotations

from typing import Mapping, Sequence
import pandas as pd
import numpy as np

from src.utils.logging import get_logger

log = get_logger(__name__)

def normalize_columns(df_raw: pd.DataFrame, rename_map: Mapping[str, str]) -> pd.DataFrame:
    df = df_raw.copy()
    
    log.info(f"DEBUG: CSV Columns found: {list(df.columns)}")
    mapped_found = [c for c in rename_map.keys() if c in df.columns]
    log.info(f"DEBUG: rename_map keys found in CSV: {mapped_found}")

    cols = {c: rename_map[c] for c in df.columns if c in rename_map}
    if cols:
        df.rename(columns=cols, inplace=True)
        log.info(f"DEBUG: Renamed columns to: {list(df.columns)}")
    return df


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "hs6" in df.columns:
        s = df["hs6"].astype(str).str.strip()
        s = s.str.extract(r"(\d+)", expand=False)
        s = s.fillna("").astype(str)
        s = s.str.slice(0, 6)
        s = s.str.zfill(6)
        s = s.replace("000000", np.nan)
        df["hs6"] = s

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    if "value" in df.columns:
        v = df["value"]
        if not pd.api.types.is_numeric_dtype(v):
            s = v.astype(str).str.strip()
            s = s.replace({"": np.nan, "nan": np.nan, "None": np.nan})
            def parse_one(x: str):
                if x is None or (isinstance(x, float) and np.isnan(x)): return np.nan
                x = str(x).strip()
                if x == "" or x.lower() == "nan": return np.nan
                x = x.replace(",", "") 
                try: return float(x)
                except: return np.nan
            df["value"] = s.map(parse_one)
        else:
            df["value"] = pd.to_numeric(v, errors="coerce")

    if "flow" in df.columns:
        df["flow"] = df["flow"].astype(str).str.strip()
        def clean_flow(x):
            x_lower = x.lower()
            if "export" in x_lower:
                return "Export"
            elif "import" in x_lower:
                return "Import"
            return x
        df["flow"] = df["flow"].apply(clean_flow)

    for c in ("reporter", "partner"):
        if c in df.columns:
            df[c] = df[c].astype(str).str.upper().str.strip()

    return df


def audit_classification_versions(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ["classificationCode", "classificationSearchCode", "isOriginalClassification"] if c in df.columns]
    if not cols:
        return pd.DataFrame([{"field": "classificationCode", "value": "MISSING", "count": len(df), "share": 1.0}])

    rows = []
    for c in cols:
        vc = df[c].astype(str).value_counts(dropna=False)
        for v, cnt in vc.items():
            rows.append({"field": c, "value": v, "count": int(cnt)})

    out = pd.DataFrame(rows)
    out["share"] = out["count"] / out["count"].sum()
    return out.sort_values(["field", "count"], ascending=[True, False])


def filter_core(
    df: pd.DataFrame,
    required_columns: Sequence[str],
    year_min: int | None = None,
    year_max: int | None = None,
    value_positive_only: bool = True,
) -> pd.DataFrame:
    df = df.copy()
    before = len(df)

    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns after renaming: {missing}")

    # --- CORREÇÃO DE DUPLA CONTAGEM (W00) NA RAIZ DO PIPELINE ---
    if "partner" in df.columns:
        df = df[~df["partner"].isin(["W00", "WLD"])]
    if "reporter" in df.columns:
        df = df[~df["reporter"].isin(["W00", "WLD"])]

    df = df.dropna(subset=list(required_columns))
    after_dropna = len(df)
    
    if after_dropna < before:
        log.warning(f"Dropped {before - after_dropna} rows due to missing values (NaN) in columns: {required_columns}")

    if "year" in df.columns:
        unique_years = sorted(df["year"].unique().tolist())
        log.info(f"DEBUG: Years found in data BEFORE filtering: {unique_years[:20]} (truncated)")

    if "year" in df.columns and (year_min or year_max):
        df["year"] = df["year"].astype(int)
        if year_min is not None:
            df = df[df["year"] >= int(year_min)]
        if year_max is not None:
            df = df[df["year"] <= int(year_max)]
    
    after_year = len(df)
    if after_year < after_dropna:
        log.info(f"Dropped {after_dropna - after_year} rows due to year filter ({year_min}-{year_max}).")

    if value_positive_only and "value" in df.columns:
        df = df[df["value"] > 0]
    
    after_val = len(df)
    log.info(f"filter_core: {before:,} -> {after_val:,} rows kept.")
    return df


def attach_basket(df: pd.DataFrame, basket_df: pd.DataFrame) -> pd.DataFrame:
    if "hs6" not in df.columns:
        raise KeyError("Expected 'hs6' column before basket join.")

    b = basket_df.copy()
    b["hs6"] = b["hs6"].astype(str).str.zfill(6)
    out = df.merge(b, on="hs6", how="inner")
    return out


def normalize_pipeline(
    df_raw: pd.DataFrame,
    rename_map: Mapping[str, str],
    required_columns: Sequence[str],
    basket_df: pd.DataFrame,
    year_min: int | None,
    year_max: int | None,
    value_positive_only: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    
    log.info(f"Starting normalization. Raw rows={len(df_raw):,}, cols={len(df_raw.columns)}")

    df = normalize_columns(df_raw, rename_map=rename_map)
    df = coerce_types(df)
    audit_cl = audit_classification_versions(df)

    before_join = len(df)
    df = attach_basket(df, basket_df=basket_df)
    log.info(f"Basket join: {before_join:,} -> {len(df):,} rows kept.")

    df = filter_core(
        df,
        required_columns=required_columns,
        year_min=year_min,
        year_max=year_max,
        value_positive_only=value_positive_only,
    )

    return df, audit_cl