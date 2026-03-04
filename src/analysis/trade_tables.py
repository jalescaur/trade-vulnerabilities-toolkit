"""
src/analysis/trade_tables.py
============================
Build standardized chapter-ready tables from the canonical dataset.

This module produces "final" tables (Excel) and is designed to be used by scripts.

Tables included (core set):
- Basket definition table (HS6 list + metadata)
- Global totals by year/flow
- HS6 shares by year/flow
- Global exporter concentration by HS6/year (HHI, CR3, CR5)
- Importer dependency (Top1 supplier share, supplier HHI)
- RCA (top exporters per HS6)
- IIT summaries (by year/HS6 or overall)
- Export diversification entropy (by exporter/year)

The calling script decides which of these become chapter outputs.
"""

from __future__ import annotations

import pandas as pd

from src.analysis.trade_metrics import (
    global_totals,
    hs6_global_shares,
    global_exporter_concentration,
    importer_supplier_concentration,
    hs6_growth_volatility,
    rca_balassa,
    iit_grubel_lloyd,
    export_diversification_entropy,
)


def table_global_totals(df: pd.DataFrame) -> pd.DataFrame:
    return global_totals(df)


def table_hs6_shares(df: pd.DataFrame) -> pd.DataFrame:
    return hs6_global_shares(df)


def table_global_exporter_concentration(df: pd.DataFrame) -> pd.DataFrame:
    return global_exporter_concentration(df, k_list=(3, 5))


def table_importer_dependency(df: pd.DataFrame) -> pd.DataFrame:
    return importer_supplier_concentration(df, k_list=(1, 3, 5))


def table_growth_volatility(df: pd.DataFrame) -> pd.DataFrame:
    return hs6_growth_volatility(df)


def table_rca_top(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    rca = rca_balassa(df)
    if rca.empty:
        return rca
    rca = rca.sort_values(["year", "hs6", "RCA"], ascending=[True, True, False])
    return rca.groupby(["year","hs6"]).head(top_n)


def table_iit_summary(df: pd.DataFrame) -> pd.DataFrame:
    iit = iit_grubel_lloyd(df)
    # summarize by year and hs6: mean IIT across countries with non-zero trade
    iit_nonzero = iit[(iit["X"] + iit["M"]) > 0].copy()
    out = (
        iit_nonzero.groupby(["year","hs6"], as_index=False)
        .agg(mean_IIT=("IIT","mean"), median_IIT=("IIT","median"), n_countries=("country","nunique"))
        .sort_values(["year","hs6"])
    )
    return out


def table_export_diversification(df: pd.DataFrame) -> pd.DataFrame:
    return export_diversification_entropy(df)