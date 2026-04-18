"""
src/analysis/country_analysis.py
=================================
Core computation engine for country- and bloc-level deep-dive analysis.

Covers:
- Resolution of free-text input to ISO3 member lists (individual countries or blocs)
- Aggregation of trade flows for blocs (sum of members)
- All trade metrics per entity (HHI, CR3, CR5, Entropy, RCA, IIT, CAGR, CV)
  computed separately for Export and Import flows
- Market-share participation of each entity per HS6 and for the basket as a whole
- Bilateral pair comparisons (exposure, asymmetry)
- Entity vs Rest-of-World comparison

All functions operate on the canonical schema:
    year, reporter, partner, hs6, flow, value
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pycountry
import yaml

from src.utils.logging import get_logger

log = get_logger(__name__)


# ============================================================
# ISO3 helpers
# ============================================================

MANUAL_ISO3: Dict[str, str] = {
    # Common name variants -> ISO3
    "usa": "USA", "united states": "USA", "united states of america": "USA", "us": "USA",
    "uk": "GBR", "united kingdom": "GBR", "britain": "GBR", "great britain": "GBR",
    "china": "CHN", "prc": "CHN", "peoples republic of china": "CHN",
    "taiwan": "TWN", "chinese taipei": "TWN",
    "south korea": "KOR", "korea": "KOR", "republic of korea": "KOR",
    "north korea": "PRK",
    "russia": "RUS", "russian federation": "RUS",
    "iran": "IRN", "islamic republic of iran": "IRN",
    "vietnam": "VNM", "viet nam": "VNM",
    "malaysia": "MYS", "malasia": "MYS",
    "hong kong": "HKG",
    "czech republic": "CZE", "czechia": "CZE",
    "slovakia": "SVK",
    "turkey": "TUR", "turkiye": "TUR",
    "uae": "ARE", "united arab emirates": "ARE",
    "saudi arabia": "SAU",
    "south africa": "ZAF",
    "new zealand": "NZL",
    "singapore": "SGP",
    "indonesia": "IDN",
    "thailand": "THA",
    "philippines": "PHL",
    "myanmar": "MMR", "burma": "MMR",
    "cambodia": "KHM",
    "laos": "LAO",
    "brunei": "BRN",
    "timor-leste": "TLS", "east timor": "TLS",
    "india": "IND",
    "pakistan": "PAK",
    "bangladesh": "BGD",
    "brazil": "BRA",
    "argentina": "ARG",
    "mexico": "MEX",
    "colombia": "COL",
    "chile": "CHL",
    "peru": "PER",
    "venezuela": "VEN",
    "ecuador": "ECU",
    "bolivia": "BOL",
    "paraguay": "PRY",
    "uruguay": "URY",
    "germany": "DEU",
    "france": "FRA",
    "italy": "ITA",
    "spain": "ESP",
    "netherlands": "NLD", "holland": "NLD",
    "belgium": "BEL",
    "sweden": "SWE",
    "norway": "NOR",
    "denmark": "DNK",
    "finland": "FIN",
    "poland": "POL",
    "austria": "AUT",
    "switzerland": "CHE",
    "portugal": "PRT",
    "greece": "GRC",
    "ireland": "IRL",
    "israel": "ISR",
    "egypt": "EGY",
    "nigeria": "NGA",
    "kenya": "KEN",
    "ethiopia": "ETH",
    "ghana": "GHA",
    "morocco": "MAR",
    "algeria": "DZA",
    "angola": "AGO",
    "japan": "JPN",
    "australia": "AUS",
    "canada": "CAN",
}


def resolve_iso3(name: str) -> Optional[str]:
    """
    Attempt to resolve a country name or ISO code to a canonical ISO3 string.
    Returns None if resolution fails.
    """
    s = name.strip()
    upper = s.upper()
    lower = s.lower()

    # Direct ISO3 match
    if len(upper) == 3 and pycountry.countries.get(alpha_3=upper):
        return upper

    # ISO2 match
    if len(upper) == 2:
        c = pycountry.countries.get(alpha_2=upper)
        if c:
            return c.alpha_3

    # Manual override
    if lower in MANUAL_ISO3:
        return MANUAL_ISO3[lower]

    # pycountry fuzzy search
    try:
        results = pycountry.countries.search_fuzzy(s)
        if results:
            return results[0].alpha_3
    except Exception:
        pass

    return None


def load_blocs(blocs_path: Path) -> Dict[str, Dict]:
    """
    Load bloc definitions from blocs.yaml.
    Returns dict: canonical_bloc_name -> {members: [ISO3, ...], aliases: [...]}
    """
    if not blocs_path.exists():
        log.warning(f"blocs.yaml not found at {blocs_path}. No bloc resolution available.")
        return {}

    with blocs_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    blocs: Dict[str, Dict] = {}
    for bloc_name, bloc_data in raw.get("blocs", {}).items():
        # members may be stored as list of strings, possibly with commas inside items
        raw_members = bloc_data.get("members", [])
        members: List[str] = []
        for item in raw_members:
            # Each item might be a comma-separated string (YAML flow sequence in a block)
            for m in str(item).replace('"', "").replace("'", "").split(","):
                m = m.strip()
                if m:
                    members.append(m)

        aliases = [a.lower() for a in bloc_data.get("aliases", [])]
        aliases.append(bloc_name.lower())

        blocs[bloc_name] = {
            "members": members,
            "aliases": aliases,
        }

    return blocs


def resolve_entity(
    token: str,
    blocs: Dict[str, Dict],
) -> Tuple[str, List[str], bool]:
    """
    Resolve a user-supplied token (country name, ISO3, or bloc name) to:
      (canonical_label, [ISO3 members], is_bloc)

    For individual countries: members = [single ISO3]
    For blocs: members = [list of ISO3]
    """
    token_lower = token.strip().lower()

    # 1) Try blocs first
    for bloc_name, bloc_data in blocs.items():
        if token_lower in bloc_data["aliases"]:
            return bloc_name, bloc_data["members"], True

    # 2) Try individual country
    iso3 = resolve_iso3(token)
    if iso3:
        # Get a nice display name
        try:
            c = pycountry.countries.get(alpha_3=iso3)
            label = c.name if c else iso3
        except Exception:
            label = iso3
        return label, [iso3], False

    log.warning(f"Could not resolve '{token}' to any known country or bloc. Skipping.")
    return token, [], False


def parse_user_input(
    raw_input: str,
    blocs: Dict[str, Dict],
) -> Dict[str, List[str]]:
    """
    Parse comma-separated user input into a dict:
      {canonical_label: [ISO3 members]}

    Empty or whitespace-only input returns an empty dict.
    """
    if not raw_input or not raw_input.strip():
        return {}

    result: Dict[str, List[str]] = {}
    tokens = [t.strip() for t in raw_input.split(",") if t.strip()]

    for token in tokens:
        label, members, is_bloc = resolve_entity(token, blocs)
        if members:
            result[label] = members
            kind = "bloc" if is_bloc else "country"
            log.info(f"  Resolved '{token}' -> {label} ({kind}, {len(members)} ISO3 member(s))")
        else:
            log.warning(f"  Could not resolve '{token}' — skipped.")

    return result


# ============================================================
# Aggregation helpers
# ============================================================

def aggregate_entity(
    df: pd.DataFrame,
    members: List[str],
    role: str = "reporter",
) -> pd.DataFrame:
    """
    Aggregate trade flows for a set of ISO3 members acting in `role` (reporter or partner).

    For bloc-level analysis we treat the union of members as a single virtual reporter/partner,
    summing their bilateral values and deduplicating intra-bloc flows.

    role='reporter': the entity is acting as exporter/importer (standard perspective)
    role='partner':  the entity is acting as the counterpart
    """
    if role == "reporter":
        sub = df[df["reporter"].isin(members)].copy()
        # Remove intra-bloc flows (reporter AND partner both inside bloc)
        sub = sub[~sub["partner"].isin(members)]
    else:
        sub = df[df["partner"].isin(members)].copy()
        sub = sub[~sub["reporter"].isin(members)]

    return sub


def world_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Global totals per year / flow / hs6 for share calculations."""
    return (
        df.groupby(["year", "flow", "hs6"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "world_value"})
    )


# ============================================================
# Metric helpers (self-contained, no external imports)
# ============================================================

def _hhi(shares: np.ndarray) -> float:
    return float(np.sum(np.square(shares)))


def _crk(shares: np.ndarray, k: int) -> float:
    s = np.sort(shares)[::-1]
    return float(s[:k].sum()) if len(s) >= k else float(s.sum())


def _entropy(shares: np.ndarray) -> float:
    s = shares[shares > 0]
    return float(-(s * np.log(s)).sum()) if len(s) else 0.0


def _cagr(first: float, last: float, n: int) -> float:
    if first <= 0 or last <= 0 or n <= 0:
        return np.nan
    return float((last / first) ** (1 / n) - 1)


def _cv(series: pd.Series) -> float:
    m = series.mean()
    if m == 0 or np.isnan(m):
        return np.nan
    return float(series.std(ddof=0) / m)


# ============================================================
# Core metrics table for one entity
# ============================================================

def compute_entity_metrics(
    df_entity: pd.DataFrame,
    df_world: pd.DataFrame,
    label: str,
    flow_filter: str,
) -> pd.DataFrame:
    """
    Compute per-HS6-per-year metrics for one entity and one flow direction.

    df_entity : subset of the master dataframe (already filtered to entity members,
                intra-bloc flows removed, but NOT yet filtered by flow)
    df_world  : full dataset (all reporters, all partners) — for RCA denominator
    flow_filter : 'Export' or 'Import'

    Returns a DataFrame with columns:
        year, hs6, flow, entity,
        entity_value, world_value, market_share,
        HHI_partners, CR3_partners, CR5_partners, Entropy_partners,
        n_partners, top_partner, top_partner_share,
        RCA, CAGR, CV, yoy_growth
    """
    fl = flow_filter

    # --- Entity flows for this direction ---
    ent = df_entity[df_entity["flow"] == fl].copy()
    if ent.empty:
        return pd.DataFrame()

    # --- World flows for this direction ---
    wld = df_world[df_world["flow"] == fl].copy()

    # --- Entity totals by year + hs6 ---
    ent_tot = (
        ent.groupby(["year", "hs6"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "entity_value"})
    )

    # --- World totals by year + hs6 ---
    wld_tot = (
        wld.groupby(["year", "hs6"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "world_value"})
    )

    base = ent_tot.merge(wld_tot, on=["year", "hs6"], how="left")
    base["world_value"] = base["world_value"].fillna(0.0)
    base["market_share"] = np.where(
        base["world_value"] > 0, base["entity_value"] / base["world_value"], np.nan
    )
    base["flow"] = fl
    base["entity"] = label

    # --- Partner concentration (who the entity trades with) ---
    partner_col = "partner" if "partner" in ent.columns else None
    conc_rows = []

    if partner_col:
        grp = ent.groupby(["year", "hs6", "partner"], as_index=False)["value"].sum()
        grp["tot"] = grp.groupby(["year", "hs6"])["value"].transform("sum")
        grp["share"] = grp["value"] / grp["tot"]

        for (yr, hs), sub in grp.groupby(["year", "hs6"]):
            shares = sub["share"].to_numpy()
            top_idx = sub["value"].idxmax()
            top_p = sub.loc[top_idx, "partner"]
            top_s = sub.loc[top_idx, "share"]
            conc_rows.append({
                "year": yr, "hs6": hs,
                "HHI_partners": _hhi(shares),
                "CR3_partners": _crk(shares, 3),
                "CR5_partners": _crk(shares, 5),
                "Entropy_partners": _entropy(shares),
                "n_partners": int(len(shares)),
                "top_partner": top_p,
                "top_partner_share": float(top_s),
            })

    if conc_rows:
        conc_df = pd.DataFrame(conc_rows)
        base = base.merge(conc_df, on=["year", "hs6"], how="left")
    else:
        for col in ["HHI_partners", "CR3_partners", "CR5_partners", "Entropy_partners",
                    "n_partners", "top_partner", "top_partner_share"]:
            base[col] = np.nan

    # --- RCA (Export only; for Import we use import dependency instead) ---
    if fl == "Export":
        # RCA = (X_cp / X_c) / (X_wp / X_w)
        X_c = ent.groupby("year")["value"].sum().rename("X_c")
        X_w = wld.groupby("year")["value"].sum().rename("X_w")
        X_cp = ent.groupby(["year", "hs6"])["value"].sum().rename("X_cp")
        X_wp = wld.groupby(["year", "hs6"])["value"].sum().rename("X_wp")

        rca_base = (
            X_cp.reset_index()
            .merge(X_c.reset_index(), on="year")
            .merge(X_wp.reset_index(), on=["year", "hs6"])
            .merge(X_w.reset_index(), on="year")
        )
        rca_base["RCA"] = (rca_base["X_cp"] / rca_base["X_c"]) / (
            rca_base["X_wp"] / rca_base["X_w"]
        )
        rca_base["RCA"] = rca_base["RCA"].replace([np.inf, -np.inf], np.nan)
        base = base.merge(rca_base[["year", "hs6", "RCA"]], on=["year", "hs6"], how="left")
    else:
        base["RCA"] = np.nan  # not applicable for imports

    # --- Growth and volatility (CAGR, CV, YoY) ---
    base = base.sort_values(["hs6", "year"]).reset_index(drop=True)
    base["yoy_growth"] = base.groupby("hs6")["entity_value"].pct_change()
    base["yoy_growth"] = base["yoy_growth"].replace([np.inf, -np.inf], np.nan)

    growth_rows = []
    for hs, sub in base.groupby("hs6"):
        sub = sub.sort_values("year")
        if len(sub) < 2:
            growth_rows.append({"hs6": hs, "CAGR": np.nan, "CV": np.nan})
            continue
        first = float(sub["entity_value"].iloc[0])
        last = float(sub["entity_value"].iloc[-1])
        n = int(sub["year"].iloc[-1]) - int(sub["year"].iloc[0])
        growth_rows.append({
            "hs6": hs,
            "CAGR": _cagr(first, last, n) if n > 0 else np.nan,
            "CV": _cv(sub["entity_value"]),
        })

    growth_df = pd.DataFrame(growth_rows)
    base = base.merge(growth_df, on="hs6", how="left")

    return base


def compute_entity_basket_totals(
    df_entity: pd.DataFrame,
    df_world: pd.DataFrame,
    label: str,
    flow_filter: str,
) -> pd.DataFrame:
    """
    Same as compute_entity_metrics but aggregated across ALL hs6 (basket totals).
    Returns one row per year.
    """
    fl = flow_filter
    ent = df_entity[df_entity["flow"] == fl].copy()
    if ent.empty:
        return pd.DataFrame()

    wld = df_world[df_world["flow"] == fl].copy()

    ent_yr = ent.groupby("year", as_index=False)["value"].sum().rename(columns={"value": "entity_value"})
    wld_yr = wld.groupby("year", as_index=False)["value"].sum().rename(columns={"value": "world_value"})

    base = ent_yr.merge(wld_yr, on="year", how="left")
    base["world_value"] = base["world_value"].fillna(0.0)
    base["market_share"] = np.where(base["world_value"] > 0, base["entity_value"] / base["world_value"], np.nan)
    base["flow"] = fl
    base["entity"] = label
    base["hs6"] = "BASKET"

    # Partner concentration across full basket
    if "partner" in ent.columns:
        grp = ent.groupby(["year", "partner"], as_index=False)["value"].sum()
        grp["tot"] = grp.groupby("year")["value"].transform("sum")
        grp["share"] = grp["value"] / grp["tot"]

        conc_rows = []
        for yr, sub in grp.groupby("year"):
            shares = sub["share"].to_numpy()
            top_idx = sub["value"].idxmax()
            conc_rows.append({
                "year": yr,
                "HHI_partners": _hhi(shares),
                "CR3_partners": _crk(shares, 3),
                "CR5_partners": _crk(shares, 5),
                "Entropy_partners": _entropy(shares),
                "n_partners": int(len(shares)),
                "top_partner": sub.loc[top_idx, "partner"],
                "top_partner_share": float(sub.loc[top_idx, "share"]),
            })
        conc_df = pd.DataFrame(conc_rows)
        base = base.merge(conc_df, on="year", how="left")
    else:
        for col in ["HHI_partners", "CR3_partners", "CR5_partners", "Entropy_partners",
                    "n_partners", "top_partner", "top_partner_share"]:
            base[col] = np.nan

    # CAGR + CV for basket totals
    base = base.sort_values("year").reset_index(drop=True)
    base["yoy_growth"] = base["entity_value"].pct_change().replace([np.inf, -np.inf], np.nan)
    if len(base) >= 2:
        first = float(base["entity_value"].iloc[0])
        last = float(base["entity_value"].iloc[-1])
        n = int(base["year"].iloc[-1]) - int(base["year"].iloc[0])
        base["CAGR"] = _cagr(first, last, n) if n > 0 else np.nan
        base["CV"] = _cv(base["entity_value"])
    else:
        base["CAGR"] = np.nan
        base["CV"] = np.nan

    base["RCA"] = np.nan  # not meaningful at basket level

    return base


# ============================================================
# Bilateral comparison
# ============================================================

def compute_bilateral(
    df: pd.DataFrame,
    label_a: str, members_a: List[str],
    label_b: str, members_b: List[str],
) -> pd.DataFrame:
    """
    Compute bilateral trade exposure between entity A and entity B.

    exposure(A->B) = value exported by A to B / total exports of A
    exposure(B->A) = value exported by B to A / total exports of B

    Also computes asymmetry = exposure(A->B) - exposure(B->A)
    Separate rows for Export and Import flows.
    """
    rows = []

    for fl in ["Export", "Import"]:
        sub = df[df["flow"] == fl].copy()

        # A exports/imports to/from B
        a_to_b = sub[sub["reporter"].isin(members_a) & sub["partner"].isin(members_b)]
        a_total = sub[sub["reporter"].isin(members_a)]

        val_a_to_b = float(a_to_b["value"].sum())
        val_a_total = float(a_total["value"].sum())
        exp_a = val_a_to_b / val_a_total if val_a_total > 0 else np.nan

        # B exports/imports to/from A
        b_to_a = sub[sub["reporter"].isin(members_b) & sub["partner"].isin(members_a)]
        b_total = sub[sub["reporter"].isin(members_b)]

        val_b_to_a = float(b_to_a["value"].sum())
        val_b_total = float(b_total["value"].sum())
        exp_b = val_b_to_a / val_b_total if val_b_total > 0 else np.nan

        rows.append({
            "flow": fl,
            "entity_A": label_a,
            "entity_B": label_b,
            f"value_{label_a}_to_{label_b}": val_a_to_b,
            f"value_{label_b}_to_{label_a}": val_b_to_a,
            f"exposure_{label_a}_to_{label_b}": exp_a,
            f"exposure_{label_b}_to_{label_a}": exp_b,
            "asymmetry (A-B)": (exp_a - exp_b) if (not np.isnan(exp_a) and not np.isnan(exp_b)) else np.nan,
        })

    return pd.DataFrame(rows)


def compute_entity_vs_row(
    df: pd.DataFrame,
    label: str,
    members: List[str],
    flow_filter: str,
) -> pd.DataFrame:
    """
    Entity vs Rest-of-World (RoW):
    RoW = all reporters NOT in members.
    Returns per-year-hs6 comparison.
    """
    fl = flow_filter
    sub = df[df["flow"] == fl].copy()

    ent = sub[sub["reporter"].isin(members)].groupby(["year", "hs6"], as_index=False)["value"].sum().rename(columns={"value": "entity_value"})
    row = sub[~sub["reporter"].isin(members)].groupby(["year", "hs6"], as_index=False)["value"].sum().rename(columns={"value": "row_value"})

    base = ent.merge(row, on=["year", "hs6"], how="outer").fillna(0.0)
    total = base["entity_value"] + base["row_value"]
    base["entity_share_of_world"] = np.where(total > 0, base["entity_value"] / total, np.nan)
    base["flow"] = fl
    base["entity"] = label

    return base


# ============================================================
# Aggregated (period) summary
# ============================================================

def period_summary(df_yearly: pd.DataFrame, value_col: str = "entity_value") -> pd.DataFrame:
    """
    Collapse yearly metrics into a single-period aggregate row.
    Numeric columns: sum for value-type cols, mean for rate/ratio cols.
    """
    if df_yearly.empty:
        return pd.DataFrame()

    value_cols = [c for c in df_yearly.columns if c in
                  ["entity_value", "world_value"]]
    rate_cols = [c for c in df_yearly.columns if c in
                 ["market_share", "HHI_partners", "CR3_partners", "CR5_partners",
                  "Entropy_partners", "top_partner_share", "RCA", "CAGR", "CV",
                  "entity_share_of_world"]]

    agg: Dict[str, object] = {}
    for c in value_cols:
        if c in df_yearly.columns:
            agg[c] = ("sum",)
    for c in rate_cols:
        if c in df_yearly.columns:
            agg[c] = ("mean",)

    # Manual aggregation to keep it readable
    out_rows = []
    group_cols = [c for c in ["entity", "hs6", "flow"] if c in df_yearly.columns]

    for keys, sub in df_yearly.groupby(group_cols):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row: Dict = dict(zip(group_cols, keys))
        row["period"] = "All Years"
        for c in value_cols:
            if c in sub.columns:
                row[c] = float(sub[c].sum())
        for c in rate_cols:
            if c in sub.columns:
                row[c] = float(sub[c].mean(skipna=True))
        # Special: recalculate market share from summed values where possible
        if "entity_value" in row and "world_value" in sub.columns:
            wv = float(sub["world_value"].sum())
            row["world_value"] = wv
            row["market_share"] = row["entity_value"] / wv if wv > 0 else np.nan
        out_rows.append(row)

    return pd.DataFrame(out_rows)