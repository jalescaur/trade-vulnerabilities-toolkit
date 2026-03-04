"""
src/analysis/trade_metrics.py
=============================
Core trade metrics widely used in international trade analysis.

This module is *general-purpose* and relies only on the canonical schema:
- year, reporter, partner, hs6, flow, value
Plus optional names:
- reporter_name, partner_name

Metrics included (mainstream in trade literature / applied trade analytics):
1) Market shares (global and by HS6)
2) Concentration (HHI, CR3, CR5) — global exporter concentration, and importer supplier concentration
3) Growth (YoY, CAGR) and volatility (CV)
4) Dependency (top supplier share, supplier HHI) from the importer's perspective
5) RCA (Balassa, 1965) based on exports
6) IIT (Grubel-Lloyd, 1975) using exports and imports
7) Diversification (entropy) for export portfolio

References (canonical):
- Balassa, B. (1965). Trade Liberalisation and "Revealed" Comparative Advantage.
- Grubel, H. & Lloyd, P. (1975). Intra-Industry Trade: The Theory and Measurement of International Trade in Differentiated Products.
- Concentration measures (HHI/CRk) are standard industrial organization tools frequently used in trade/supply-chain vulnerability analysis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------
# Helpers
# ---------------------------

def _shares(values: pd.Series) -> pd.Series:
    s = values / values.sum()
    return s.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def hhi_from_shares(shares: np.ndarray) -> float:
    """Herfindahl–Hirschman Index: sum_i share_i^2."""
    return float(np.sum(np.square(shares)))


def crk_from_shares(shares: np.ndarray, k: int) -> float:
    """Concentration ratio CRk: sum of top-k shares."""
    s = np.sort(shares)[::-1]
    return float(s[:k].sum()) if len(s) else 0.0


def entropy_from_shares(shares: np.ndarray) -> float:
    """Shannon entropy (higher = more diversified)."""
    s = shares[shares > 0]
    return float(-(s * np.log(s)).sum()) if len(s) else 0.0


def coefficient_of_variation(x: pd.Series) -> float:
    """CV = std/mean (volatility proxy)."""
    m = x.mean()
    if m == 0 or np.isnan(m):
        return np.nan
    return float(x.std(ddof=0) / m)


# ---------------------------
# 1) Global totals and shares
# ---------------------------

def global_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Total trade value by year and flow."""
    return (
        df.groupby(["year", "flow"], as_index=False)["value"].sum()
          .rename(columns={"value": "total_value"})
          .sort_values(["year", "flow"])
    )


def global_hs6_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Total trade by year, flow, and HS6."""
    return (
        df.groupby(["year", "flow", "hs6"], as_index=False)["value"].sum()
          .rename(columns={"value": "hs6_value"})
          .sort_values(["year", "flow", "hs6_value"], ascending=[True, True, False])
    )


def hs6_global_shares(df: pd.DataFrame) -> pd.DataFrame:
    """HS6 share of basket total by year and flow."""
    g = global_hs6_totals(df)
    g["basket_total"] = g.groupby(["year", "flow"])["hs6_value"].transform("sum")
    g["share_of_basket"] = g["hs6_value"] / g["basket_total"]
    return g


# ---------------------------
# 2) Concentration
# ---------------------------

def global_exporter_concentration(df: pd.DataFrame, k_list=(3, 5)) -> pd.DataFrame:
    """
    Global exporter concentration for each HS6 and year using EXPORT flows.

    For Export rows:
      exporter = reporter
      importer = partner

    Output:
      year, hs6, HHI, CR3, CR5, n_exporters
    """
    d = df[df["flow"].str.lower().eq("export")].copy()
    if d.empty:
        return pd.DataFrame(columns=["year", "hs6", "HHI", "CR3", "CR5", "n_exporters"])

    g = d.groupby(["year", "hs6", "reporter"], as_index=False)["value"].sum()
    g["share"] = g.groupby(["year", "hs6"])["value"].transform(_shares)

    def agg(sub):
        shares = sub["share"].to_numpy()
        out = {
            "HHI": hhi_from_shares(shares),
            "n_exporters": int(len(shares)),
        }
        for k in k_list:
            out[f"CR{k}"] = crk_from_shares(shares, k)
        return pd.Series(out)

    out = g.groupby(["year", "hs6"]).apply(agg).reset_index()
    return out.sort_values(["year", "HHI"], ascending=[True, False])


def importer_supplier_concentration(df: pd.DataFrame, k_list=(1, 3, 5)) -> pd.DataFrame:
    """
    Importer-side supplier concentration using IMPORT flows.

    For Import rows:
      importer = reporter
      supplier = partner

    Output:
      year, hs6, importer, top_supplier, Top1_share, HHI_suppliers, CR3, CR5, n_suppliers
    """
    d = df[df["flow"].str.lower().eq("import")].copy()
    if d.empty:
        return pd.DataFrame()

    g = d.groupby(["year", "hs6", "reporter", "partner"], as_index=False)["value"].sum()
    g["importer_total"] = g.groupby(["year", "hs6", "reporter"])["value"].transform("sum")
    g["supplier_share"] = g["value"] / g["importer_total"]

    # Top supplier per importer-hs6-year
    top = (
        g.sort_values(["year", "hs6", "reporter", "supplier_share"], ascending=[True, True, True, False])
         .groupby(["year", "hs6", "reporter"]).head(1)
         .rename(columns={"partner": "top_supplier", "supplier_share": "Top1_share"})
    )

    # Concentration metrics per importer-hs6-year
    def agg(sub):
        shares = sub["supplier_share"].to_numpy()
        out = {
            "HHI_suppliers": hhi_from_shares(shares),
            "n_suppliers": int(len(shares)),
        }
        for k in k_list:
            out[f"CR{k}"] = crk_from_shares(shares, k)
        return pd.Series(out)

    conc = g.groupby(["year", "hs6", "reporter"]).apply(agg).reset_index()

    out = conc.merge(top[["year", "hs6", "reporter", "top_supplier", "Top1_share"]], on=["year", "hs6", "reporter"], how="left")
    out = out.rename(columns={"reporter": "importer"})
    return out.sort_values(["year", "hs6", "Top1_share"], ascending=[True, True, False])


# ---------------------------
# 3) Growth and volatility
# ---------------------------

def yoy_growth(series: pd.Series) -> pd.Series:
    """Year-over-year growth for a time series sorted by year."""
    return series.pct_change().replace([np.inf, -np.inf], np.nan)


def cagr(first: float, last: float, n_periods: int) -> float:
    """Compound annual growth rate."""
    if first <= 0 or last <= 0 or n_periods <= 0:
        return np.nan
    return float((last / first) ** (1 / n_periods) - 1)


def hs6_growth_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """
    Growth and volatility for HS6 totals (by flow).
    Produces:
      - YoY growth (per year)
      - CAGR over full window (per hs6-flow)
      - CV (volatility) over full window
    """
    g = global_hs6_totals(df).copy()
    g = g.sort_values(["flow", "hs6", "year"])

    # YoY
    g["yoy_growth"] = g.groupby(["flow", "hs6"])["hs6_value"].apply(yoy_growth)

    # Window-level stats
    stats = []
    for (flow, hs6), sub in g.groupby(["flow", "hs6"]):
        sub = sub.sort_values("year")
        first = float(sub["hs6_value"].iloc[0])
        last = float(sub["hs6_value"].iloc[-1])
        n = int(sub["year"].iloc[-1] - sub["year"].iloc[0])
        stats.append({
            "flow": flow,
            "hs6": hs6,
            "CAGR": cagr(first, last, n) if n > 0 else np.nan,
            "CV": coefficient_of_variation(sub["hs6_value"]),
        })
    stats_df = pd.DataFrame(stats)

    return g.merge(stats_df, on=["flow", "hs6"], how="left")


# ---------------------------
# 4) RCA (Balassa)
# ---------------------------

def rca_balassa(df: pd.DataFrame) -> pd.DataFrame:
    """
    Balassa RCA using EXPORT flows:
      RCA_{c,p} = (X_{c,p} / X_{c,all}) / (X_{world,p} / X_{world,all})

    Returns:
      year, exporter, hs6, RCA
    """
    d = df[df["flow"].str.lower().eq("export")].copy()
    if d.empty:
        return pd.DataFrame(columns=["year", "exporter", "hs6", "RCA"])

    cp = d.groupby(["year", "reporter", "hs6"], as_index=False)["value"].sum().rename(columns={"reporter": "exporter", "value": "X_cp"})
    c_all = d.groupby(["year", "reporter"], as_index=False)["value"].sum().rename(columns={"reporter": "exporter", "value": "X_c"})
    w_p = d.groupby(["year", "hs6"], as_index=False)["value"].sum().rename(columns={"value": "X_wp"})
    w_all = d.groupby(["year"], as_index=False)["value"].sum().rename(columns={"value": "X_w"})

    out = cp.merge(c_all, on=["year", "exporter"]).merge(w_p, on=["year", "hs6"]).merge(w_all, on=["year"])
    out["RCA"] = (out["X_cp"] / out["X_c"]) / (out["X_wp"] / out["X_w"])
    return out[["year", "exporter", "hs6", "RCA"]].replace([np.inf, -np.inf], np.nan)


# ---------------------------
# 5) IIT (Grubel–Lloyd)
# ---------------------------

def iit_grubel_lloyd(df: pd.DataFrame) -> pd.DataFrame:
    """
    Grubel-Lloyd IIT index for each country-product-year:
      IIT = 1 - |X - M| / (X + M)
    (Defined when X+M>0; else NaN)

    Uses:
      exports: flow=Export, reporter=c
      imports: flow=Import, reporter=c
    Returns:
      year, country, hs6, X, M, IIT
    """
    ex = df[df["flow"].str.lower().eq("export")].groupby(["year", "reporter", "hs6"], as_index=False)["value"].sum().rename(columns={"reporter":"country","value":"X"})
    im = df[df["flow"].str.lower().eq("import")].groupby(["year", "reporter", "hs6"], as_index=False)["value"].sum().rename(columns={"reporter":"country","value":"M"})

    out = ex.merge(im, on=["year","country","hs6"], how="outer").fillna(0.0)
    denom = out["X"] + out["M"]
    out["IIT"] = np.where(denom > 0, 1 - (out["X"] - out["M"]).abs() / denom, np.nan)
    return out


# ---------------------------
# 6) Diversification (entropy) for export portfolio
# ---------------------------

def export_diversification_entropy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Export portfolio diversification per exporter-year:
    - entropy of HS6 export shares (higher -> more diversified)
    """
    d = df[df["flow"].str.lower().eq("export")].copy()
    if d.empty:
        return pd.DataFrame(columns=["year","exporter","entropy","n_products"])

    g = d.groupby(["year","reporter","hs6"], as_index=False)["value"].sum().rename(columns={"reporter":"exporter"})
    g["share"] = g.groupby(["year","exporter"])["value"].transform(_shares)

    def agg(sub):
        s = sub["share"].to_numpy()
        return pd.Series({
            "entropy": entropy_from_shares(s),
            "n_products": int(len(s))
        })

    out = g.groupby(["year","exporter"]).apply(agg).reset_index()
    return out.sort_values(["year","entropy"], ascending=[True, False])