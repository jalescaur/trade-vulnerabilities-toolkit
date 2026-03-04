"""
src/io/normalize.py
===================
Config-driven normalization for COMTRADE-like exports.

This module is intentionally general:
- It does NOT assume a single fixed column schema
- It uses `rename_map` from YAML config to map raw fields -> canonical fields

Canonical fields expected downstream:
- year, reporter, partner, hs6, value
Optional but recommended:
- flow
Optional for better labels:
- reporter_name_raw, partner_name_raw

Classification metadata:
- We do not enforce a single HS edition here.
- We audit `classificationCode` / `classificationSearchCode` when present.
"""

from __future__ import annotations

from typing import Mapping, Sequence
import pandas as pd

from src.utils.logging import get_logger

log = get_logger(__name__)


def normalize_columns(df_raw: pd.DataFrame, rename_map: Mapping[str, str]) -> pd.DataFrame:
    """Rename raw columns according to config mapping; preserve unknown columns."""
    df = df_raw.copy()
    cols = {c: rename_map[c] for c in df.columns if c in rename_map}
    if cols:
        df.rename(columns=cols, inplace=True)
    return df


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Coerce types for canonical fields when present.
    - hs6 -> 6-digit string
    - year -> int
    - value -> float
    - reporter/partner -> uppercase
    """
    df = df.copy()

    if "hs6" in df.columns:
        df["hs6"] = (
            df["hs6"]
            .astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(6)
        )

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")

    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    for c in ("reporter", "partner"):
        if c in df.columns:
            df[c] = df[c].astype(str).str.upper()

    if "flow" in df.columns:
        df["flow"] = df["flow"].astype(str)

    return df


def audit_classification_versions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Audit classification metadata fields if present.
    This helps document HS version consistency (when the export includes these fields).
    """
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
    """
    Apply minimal validity filters and the study window.
    Keeps policy explicit and configurable.

    required_columns:
      columns that must be non-null to keep a row (e.g., year, reporter, partner, hs6, value)
    """
    df = df.copy()
    before = len(df)

    # Ensure required cols exist
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns after renaming: {missing}")

    df = df.dropna(subset=list(required_columns))

    # year window
    if "year" in df.columns:
        df["year"] = df["year"].astype(int)
        if year_min is not None:
            df = df[df["year"] >= int(year_min)]
        if year_max is not None:
            df = df[df["year"] <= int(year_max)]

    # positive values
    if value_positive_only and "value" in df.columns:
        df = df[df["value"] > 0]

    after = len(df)
    log.info(f"filter_core: {before:,} -> {after:,} rows kept.")
    return df


def attach_basket(df: pd.DataFrame, basket_df: pd.DataFrame) -> pd.DataFrame:
    """
    Inner-join with the basket HS6 list to keep ONLY analyzable codes.
    basket_df must have a column `hs6`.
    """
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
    """
    Full normalization pipeline (config-driven).

    Returns
    -------
    df_norm: normalized + basket-filtered + filtered dataset
    audit_cl: classification audit table
    """
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

    log.info(f"Normalization complete. Final rows={len(df):,}, cols={len(df.columns)}")
    return df, audit_cl