"""
scripts/13_country_deep_dive.py
================================
Country and bloc deep-dive analysis.

Generates per-entity Excel workbooks (one per country/bloc) and a comparative
workbook covering all selected entities side by side.

Usage:
  python scripts/13_country_deep_dive.py --config configs/default.yaml
                                         --entities "USA, China, ASEAN, European Union"
                                         [--blocs configs/blocs.yaml]

If --entities is not supplied (e.g. called from run_all.py after terminal input),
the script reads the COUNTRY_ENTITIES environment variable. If that is also absent
it exits cleanly without generating any output.

Output structure:
  outputs/countries/
    <EntityName>/
      <EntityName>_Export.xlsx
      <EntityName>_Import.xlsx
    _comparative/
      Comparative_Export.xlsx
      Comparative_Import.xlsx
      Bilateral_Pairs.xlsx
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import pycountry

from src.runtime_config import load_config, cfg_paths
from src.utils.logging import get_logger
from src.analysis.country_analysis import (
    load_blocs,
    parse_user_input,
    aggregate_entity,
    compute_entity_metrics,
    compute_entity_basket_totals,
    compute_bilateral,
    compute_entity_vs_row,
    period_summary,
)

log = get_logger(__name__)

# ============================================================
# Glossary — appears as first sheet in every workbook
# ============================================================

GLOSSARY = pd.DataFrame([
    {
        "Term / Metric": "Market Share",
        "Symbol": "—",
        "Definition": (
            "The proportion of global trade value (USD) accounted for by the entity "
            "(country or bloc) for a given product (HS6) or the full basket, in a given "
            "year or aggregated period. Computed as entity_value / world_value."
        ),
        "Interpretation": "Higher values indicate greater global relevance. Values near 1.0 imply near-monopoly.",
        "Reference": "Standard trade statistics; cf. UN Comtrade documentation.",
    },
    {
        "Term / Metric": "HHI — Herfindahl–Hirschman Index",
        "Symbol": "HHI",
        "Definition": (
            "Sum of squared partner shares: HHI = Σ(share_i²). Computed here over the "
            "entity's trading partners (either export destinations or import sources). "
            "Ranges from 0 (perfectly diversified) to 1 (single partner)."
        ),
        "Interpretation": (
            "HHI > 0.25: highly concentrated (oligopoly / single-partner dependence). "
            "0.10–0.25: moderate concentration. < 0.10: competitive / diversified partner base."
        ),
        "Reference": "Hirschman (1964); widely applied in industrial organisation and trade vulnerability analyses.",
    },
    {
        "Term / Metric": "CR3 — Three-Partner Concentration Ratio",
        "Symbol": "CR3",
        "Definition": (
            "Sum of the shares of the top 3 trading partners. "
            "CR3 = share_1 + share_2 + share_3."
        ),
        "Interpretation": (
            "CR3 > 0.80 indicates that three partners account for over 80 % of the entity's "
            "trade in that product — a sign of high exposure."
        ),
        "Reference": "Bain (1951); standard industrial-organisation concentration measure.",
    },
    {
        "Term / Metric": "CR5 — Five-Partner Concentration Ratio",
        "Symbol": "CR5",
        "Definition": "Sum of the shares of the top 5 trading partners.",
        "Interpretation": "Same logic as CR3 but captures a wider oligopoly tier.",
        "Reference": "Bain (1951).",
    },
    {
        "Term / Metric": "Shannon Entropy",
        "Symbol": "H",
        "Definition": (
            "H = −Σ(share_i · ln(share_i)). Measures the diversity of the partner portfolio. "
            "Higher entropy = more evenly spread trade across many partners."
        ),
        "Interpretation": (
            "Low entropy (near 0): trade is highly concentrated in few partners. "
            "High entropy: broad, diversified partner base conferring supply-chain resilience."
        ),
        "Reference": "Shannon (1948); extensively used in trade diversification literature.",
    },
    {
        "Term / Metric": "RCA — Revealed Comparative Advantage",
        "Symbol": "RCA",
        "Definition": (
            "Balassa Index: RCA = (X_cp / X_c) / (X_wp / X_w), where X_cp = country exports "
            "of product p, X_c = total country exports, X_wp = world exports of p, "
            "X_w = total world exports. Computed on Export flows only."
        ),
        "Interpretation": (
            "RCA > 1.0: the entity has a revealed comparative advantage (exports this product "
            "at a higher intensity than the global average). "
            "RCA < 1.0: comparative disadvantage."
        ),
        "Reference": "Balassa (1965).",
    },
    {
        "Term / Metric": "CAGR — Compound Annual Growth Rate",
        "Symbol": "CAGR",
        "Definition": (
            "CAGR = (last_value / first_value)^(1/n) − 1, where n = number of years "
            "between first and last observation."
        ),
        "Interpretation": (
            "Positive CAGR: the entity's trade in the product grew over the study period. "
            "Negative: contraction. Smooths out year-to-year volatility."
        ),
        "Reference": "Standard financial/trade growth measure.",
    },
    {
        "Term / Metric": "CV — Coefficient of Variation",
        "Symbol": "CV",
        "Definition": "CV = standard deviation / mean, computed on the annual trade values.",
        "Interpretation": (
            "High CV: erratic, volatile trade behaviour — susceptibility to supply/demand shocks. "
            "Low CV: stable, predictable trade relationship."
        ),
        "Reference": "Standard statistical measure.",
    },
    {
        "Term / Metric": "YoY Growth",
        "Symbol": "yoy_growth",
        "Definition": "Year-on-year percentage change in trade value: (value_t / value_{t-1}) − 1.",
        "Interpretation": "Captures annual dynamics and turning points.",
        "Reference": "Standard trade statistics.",
    },
    {
        "Term / Metric": "Top Partner Share",
        "Symbol": "top_partner_share",
        "Definition": (
            "Share of the entity's total trade (for the given HS6 and flow) accounted for by "
            "its single most important trading partner."
        ),
        "Interpretation": "A high value signals structural dependence on a single counterpart.",
        "Reference": "Derived from supplier/buyer concentration literature.",
    },
    {
        "Term / Metric": "Entity vs Rest-of-World",
        "Symbol": "entity_share_of_world",
        "Definition": (
            "The entity's share of total global trade in each HS6: "
            "entity_value / (entity_value + all_other_reporters_value)."
        ),
        "Interpretation": "Provides a clean measure of global market presence independent of absolute values.",
        "Reference": "Standard trade-share decomposition.",
    },
    {
        "Term / Metric": "Bilateral Exposure",
        "Symbol": "exposure(A→B)",
        "Definition": (
            "exposure(A→B) = value traded between A and B / total value traded by A. "
            "Computed separately for Export and Import flows."
        ),
        "Interpretation": (
            "High exposure(A→B): A is heavily dependent on B as a destination (export) "
            "or source (import). High asymmetry: one side is far more exposed than the other."
        ),
        "Reference": (
            "Derived from vulnerability literature; cf. Gaulier & Zignago (2010) on bilateral dependence."
        ),
    },
    {
        "Term / Metric": "Asymmetry",
        "Symbol": "asymmetry(A,B)",
        "Definition": "asymmetry(A,B) = exposure(A→B) − exposure(B→A).",
        "Interpretation": (
            "Positive: A is more exposed to B than B is to A (A holds the weaker geoeconomic position). "
            "Negative: B is more exposed to A."
        ),
        "Reference": "Bilateral dependence asymmetry; standard in geoeconomics literature.",
    },
    {
        "Term / Metric": "Basket",
        "Symbol": "BASKET",
        "Definition": (
            "The full set of HS6 codes defined in the project configuration (basket.hs6). "
            "When hs6 = 'BASKET', figures represent the aggregate across all codes in the basket."
        ),
        "Interpretation": "Provides a holistic view of the entity's position in the AI infrastructure supply chain.",
        "Reference": "Project-specific operational definition.",
    },
    {
        "Term / Metric": "Flow: Export",
        "Symbol": "Export",
        "Definition": (
            "Goods shipped FROM the reporting country TO a partner country. "
            "In UN Comtrade, Export flows are reported by the exporting country."
        ),
        "Interpretation": "Captures supply-side / production capacity of the reporting entity.",
        "Reference": "UN Comtrade / UNSD trade statistics methodology.",
    },
    {
        "Term / Metric": "Flow: Import",
        "Symbol": "Import",
        "Definition": (
            "Goods received BY the reporting country FROM a partner country. "
            "In UN Comtrade, Import flows are reported by the importing country."
        ),
        "Interpretation": "Captures demand-side / dependency profile of the reporting entity.",
        "Reference": "UN Comtrade / UNSD trade statistics methodology.",
    },
    {
        "Term / Metric": "HS6",
        "Symbol": "hs6",
        "Definition": (
            "Six-digit Harmonised System code (World Customs Organisation). "
            "Each code identifies a specific product category. "
            "Codes used in this project are defined in the basket configuration."
        ),
        "Interpretation": "Granular product-level lens for trade analysis.",
        "Reference": "World Customs Organisation (WCO); UN Comtrade.",
    },
    {
        "Term / Metric": "ISO3",
        "Symbol": "ISO3",
        "Definition": (
            "Three-letter country code as defined by ISO 3166-1 alpha-3. "
            "Blocs (e.g. ASEAN, EU) are aggregated from their member ISO3 codes."
        ),
        "Interpretation": "Standard country identifier used throughout the dataset.",
        "Reference": "ISO 3166-1; UN Statistics Division.",
    },
])


# ============================================================
# Excel writing helpers
# ============================================================

def _get_country_name(iso3: str) -> str:
    if not iso3 or pd.isna(iso3):
        return ""
    overrides = {"TWN": "Taiwan", "S19": "Taiwan", "WLD": "World", "EU2": "European Union", "HKG": "Hong Kong"}
    if iso3 in overrides:
        return overrides[iso3]
    try:
        c = pycountry.countries.get(alpha_3=iso3)
        return c.name if c else iso3
    except Exception:
        return iso3


def _inject_country_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["top_partner", "reporter", "partner", "entity_A", "entity_B", "supplier", "entity"]:
        if col in df.columns:
            name_col = f"{col}_name"
            # Only add name col if values look like ISO3 (3 uppercase letters)
            sample = df[col].dropna().astype(str)
            if sample.empty:
                continue
            looks_like_iso3 = sample.str.match(r"^[A-Z]{3}$").mean() > 0.5
            if looks_like_iso3:
                df[name_col] = df[col].apply(_get_country_name)
                cols = list(df.columns)
                cols.remove(name_col)
                idx = cols.index(col)
                cols.insert(idx + 1, name_col)
                df = df[cols]
    return df


def _safe_sheet_name(name: str) -> str:
    """Excel sheet names: max 31 chars, no special chars."""
    for ch in r'\/*?:[]':
        name = name.replace(ch, "_")
    return name[:31]


def _write_sheet(writer: pd.ExcelWriter, df: pd.DataFrame, sheet: str, inject_names: bool = True):
    if inject_names:
        df = _inject_country_names(df)
    df.to_excel(writer, sheet_name=_safe_sheet_name(sheet), index=False)


def _format_pct(val):
    if pd.isna(val):
        return val
    return round(float(val) * 100, 4)  # store as decimal; Excel formatting handles display


# ============================================================
# Per-entity workbook builder
# ============================================================

def build_entity_workbook(
    df: pd.DataFrame,
    label: str,
    members: List[str],
    out_dir: Path,
    flow: str,
):
    """
    Build one Excel workbook for `label` and one flow direction.
    Sheets:
      0_Glossary | 1_ByYear_ByHS6 | 2_ByYear_Basket | 3_Period_ByHS6 | 4_Period_Basket
      5_vs_RestOfWorld_ByHS6 | 6_vs_RestOfWorld_Basket
    """
    # Aggregate entity flows (remove intra-bloc)
    df_ent = aggregate_entity(df, members, role="reporter")

    yearly_hs6 = compute_entity_metrics(df_ent, df, label, flow)
    yearly_basket = compute_entity_basket_totals(df_ent, df, label, flow)

    period_hs6 = period_summary(yearly_hs6) if not yearly_hs6.empty else pd.DataFrame()
    period_bask = period_summary(yearly_basket) if not yearly_basket.empty else pd.DataFrame()

    row_hs6 = compute_entity_vs_row(df, label, members, flow)
    row_bask = compute_entity_vs_row(
        df.assign(hs6="BASKET"),
        label, members, flow
    ) if not df.empty else pd.DataFrame()

    safe_label = label.replace(" ", "_").replace("/", "_")
    path = out_dir / f"{safe_label}_{flow}.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        GLOSSARY.to_excel(writer, sheet_name="0_Glossary", index=False)

        if not yearly_hs6.empty:
            _write_sheet(writer, yearly_hs6, "1_ByYear_ByHS6")
        if not yearly_basket.empty:
            _write_sheet(writer, yearly_basket, "2_ByYear_Basket")
        if not period_hs6.empty:
            _write_sheet(writer, period_hs6, "3_Period_ByHS6")
        if not period_bask.empty:
            _write_sheet(writer, period_bask, "4_Period_Basket")
        if not row_hs6.empty:
            _write_sheet(writer, row_hs6, "5_vs_RoW_ByHS6")
        if not row_bask.empty:
            _write_sheet(writer, row_bask, "6_vs_RoW_Basket")

    log.info(f"  Written: {path}")
    return path


# ============================================================
# Comparative workbook builder
# ============================================================

def build_comparative_workbook(
    df: pd.DataFrame,
    entities: Dict[str, List[str]],
    out_dir: Path,
    flow: str,
):
    """
    Build comparative workbook covering all selected entities.
    Sheets:
      0_Glossary | 1_All_ByYear_ByHS6 | 2_All_ByYear_Basket
      3_All_Period_ByHS6 | 4_All_Period_Basket
      5_Bilateral_<A>_vs_<B> (one per pair)
    """
    path = out_dir / f"Comparative_{flow}.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)

    all_yearly_hs6: List[pd.DataFrame] = []
    all_yearly_bask: List[pd.DataFrame] = []

    for label, members in entities.items():
        df_ent = aggregate_entity(df, members, role="reporter")

        yh = compute_entity_metrics(df_ent, df, label, flow)
        yb = compute_entity_basket_totals(df_ent, df, label, flow)

        if not yh.empty:
            all_yearly_hs6.append(yh)
        if not yb.empty:
            all_yearly_bask.append(yb)

    comb_hs6 = pd.concat(all_yearly_hs6, ignore_index=True) if all_yearly_hs6 else pd.DataFrame()
    comb_bask = pd.concat(all_yearly_bask, ignore_index=True) if all_yearly_bask else pd.DataFrame()

    period_hs6 = period_summary(comb_hs6) if not comb_hs6.empty else pd.DataFrame()
    period_bask = period_summary(comb_bask) if not comb_bask.empty else pd.DataFrame()

    # All pairs
    pairs = list(itertools.combinations(entities.items(), 2))

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        GLOSSARY.to_excel(writer, sheet_name="0_Glossary", index=False)

        if not comb_hs6.empty:
            _write_sheet(writer, comb_hs6, "1_All_ByYear_ByHS6")
        if not comb_bask.empty:
            _write_sheet(writer, comb_bask, "2_All_ByYear_Basket")
        if not period_hs6.empty:
            _write_sheet(writer, period_hs6, "3_All_Period_ByHS6")
        if not period_bask.empty:
            _write_sheet(writer, period_bask, "4_All_Period_Basket")

        for (label_a, members_a), (label_b, members_b) in pairs:
            bil = compute_bilateral(df, label_a, members_a, label_b, members_b)
            sheet = f"Bil_{_safe_sheet_name(label_a)[:10]}_vs_{_safe_sheet_name(label_b)[:10]}"
            if not bil.empty:
                bil.to_excel(writer, sheet_name=_safe_sheet_name(sheet), index=False)

        # Each entity vs RoW summary
        row_rows = []
        for label, members in entities.items():
            r = compute_entity_vs_row(df, label, members, flow)
            if not r.empty:
                row_rows.append(r)
        if row_rows:
            row_all = pd.concat(row_rows, ignore_index=True)
            _write_sheet(writer, row_all, "RoW_All_ByHS6")

    log.info(f"  Written: {path}")
    return path


# ============================================================
# Main
# ============================================================

import itertools


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--entities", default=None, help="Comma-separated list of countries/blocs.")
    p.add_argument("--blocs", default="configs/blocs.yaml", help="Path to blocs.yaml.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    # --- Resolve entity input ---
    raw_input = args.entities or os.environ.get("COUNTRY_ENTITIES", "")
    if not raw_input or not raw_input.strip():
        log.info("No countries/blocs specified. Skipping country deep-dive.")
        return

    blocs_path = Path(args.blocs)
    blocs = load_blocs(blocs_path)
    entities: Dict[str, List[str]] = parse_user_input(raw_input, blocs)

    if not entities:
        log.warning("No valid entities resolved from input. Skipping.")
        return

    log.info(f"Entities resolved: {list(entities.keys())}")

    # --- Load data ---
    in_path = paths["processed_root"] / "intermediate_tables" / (
        cfg["outputs"]["intermediate_dataset_name"].replace(".parquet", "_country_names.parquet")
    )
    if not in_path.exists():
        in_path = paths["intermediate_dataset"]
    if not in_path.exists():
        raise FileNotFoundError(
            f"Intermediate dataset not found: {in_path}\n"
            f"Run: python scripts/01_build_dataset.py --config {args.config}"
        )

    df = pd.read_parquet(in_path)
    log.info(f"Loaded: {in_path} | rows={len(df):,}")

    out_root = Path("outputs") / "countries"
    comp_dir = out_root / "_comparative"

    # --- Per-entity workbooks ---
    for label, members in entities.items():
        safe = label.replace(" ", "_").replace("/", "_")
        ent_dir = out_root / safe
        ent_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Building workbooks for: {label}")
        for flow in ["Export", "Import"]:
            build_entity_workbook(df, label, members, ent_dir, flow)

    # --- Comparative workbooks ---
    if len(entities) > 1:
        comp_dir.mkdir(parents=True, exist_ok=True)
        log.info("Building comparative workbooks...")
        for flow in ["Export", "Import"]:
            build_comparative_workbook(df, entities, comp_dir, flow)

    log.info("Country deep-dive complete ✅")


if __name__ == "__main__":
    main()