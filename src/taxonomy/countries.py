"""
src/taxonomy/countries.py
=========================
Country name standardization (English).

Goal:
- Keep all entities in the dataset.
- Add explicit "full country name" columns for reporter and partner.

Strategy:
1) Prefer Comtrade-provided descriptors (reporterDesc/partnerDesc), which are typically English and
   cover non-standard entities/territories better than ISO alone.
2) Fall back to ISO 3166-1 alpha-3 lookups via pycountry.
3) Apply manual overrides for known edge cases (Taiwan, etc.).
4) If all fails, keep the original code (still traceable).

References (conceptual/provenance):
- ISO 3166-1 alpha-3 standard (implemented via pycountry).
- UN Comtrade provides reporter/partner descriptions in exports (reporterDesc/partnerDesc).

Note on Taiwan:
- Comtrade commonly uses ISO3 'TWN' and description "Taiwan, Province of China" (varies by source).
- For readability in the manuscript, we standardize to "Taiwan".
"""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

import pycountry


# Manual overrides for readability / common dataset quirks.
# Keep this SMALL and auditable.
MANUAL_NAME_OVERRIDES: dict[str, str] = {
    "TWN": "Taiwan",
    "S19": "Taiwan",
    # Optional future edge cases (only add if they actually appear):
    "XKX": "Kosovo",
    "ROM": "Romania",   # (rare legacy)
}


def iso3_to_english_name(iso3: str) -> str | None:
    """
    ISO3 -> English country name using pycountry.
    Returns None if not found.

    pycountry names follow ISO registry conventions, which may differ slightly
    from Comtrade descriptions (e.g., punctuation, "Republic of ...").
    """
    if iso3 is None:
        return None
    code = str(iso3).upper()

    if code in MANUAL_NAME_OVERRIDES:
        return MANUAL_NAME_OVERRIDES[code]

    try:
        country = pycountry.countries.get(alpha_3=code)
        if country is None:
            return None
        # pycountry sometimes includes official long forms; 'name' is usually fine for tables.
        return country.name
    except Exception:
        return None


def clean_comtrade_desc(desc: str, iso3: str | None = None) -> str | None:
    """
    Clean Comtrade-provided country/area descriptions for manuscript readability.

    We keep this conservative:
    - Trim whitespace
    - Optionally standardize Taiwan wording
    """
    if desc is None:
        return None

    s = str(desc).strip()
    if not s or s.lower() == "nan":
        return None

    # Standardize Taiwan naming if Comtrade returns the ISO long form
    if iso3 is not None and str(iso3).upper() == "TWN":
        return "Taiwan"

    # You can add other gentle cleanups here IF needed, but keep minimal.
    return s


def add_country_names(
    df: pd.DataFrame,
    reporter_iso_col: str = "reporter",
    partner_iso_col: str = "partner",
    reporter_desc_col: str = "reporter_name_raw",
    partner_desc_col: str = "partner_name_raw",
    reporter_name_col: str = "reporter_name",
    partner_name_col: str = "partner_name",
) -> pd.DataFrame:
    """
    Add English full names for reporter and partner.

    Output columns:
    - reporter_name
    - partner_name

    We do NOT drop ISO codes: keep them for merges and compact references.
    """
    out = df.copy()

    # Reporter name resolution:
    # 1) Comtrade desc (cleaned)
    # 2) pycountry via ISO3
    rep_desc = None
    if reporter_desc_col in out.columns:
        rep_desc = out[reporter_desc_col]
    out[reporter_name_col] = None

    if rep_desc is not None:
        out[reporter_name_col] = [
            clean_comtrade_desc(d, iso3=iso3) for d, iso3 in zip(rep_desc, out[reporter_iso_col])
        ]

    # Fill remaining nulls from ISO
    mask = out[reporter_name_col].isna()
    if mask.any():
        out.loc[mask, reporter_name_col] = out.loc[mask, reporter_iso_col].apply(iso3_to_english_name)

    # If still null: keep ISO code (so no missing names)
    mask = out[reporter_name_col].isna()
    out.loc[mask, reporter_name_col] = out.loc[mask, reporter_iso_col].astype(str)

    # Partner name resolution:
    par_desc = None
    if partner_desc_col in out.columns:
        par_desc = out[partner_desc_col]
    out[partner_name_col] = None

    if par_desc is not None:
        out[partner_name_col] = [
            clean_comtrade_desc(d, iso3=iso3) for d, iso3 in zip(par_desc, out[partner_iso_col])
        ]

    mask = out[partner_name_col].isna()
    if mask.any():
        out.loc[mask, partner_name_col] = out.loc[mask, partner_iso_col].apply(iso3_to_english_name)

    mask = out[partner_name_col].isna()
    out.loc[mask, partner_name_col] = out.loc[mask, partner_iso_col].astype(str)

    return out


def audit_country_name_coverage(df: pd.DataFrame, name_cols=("reporter_name", "partner_name")) -> pd.DataFrame:
    """
    Quick audit: ensure names are fully populated (no nulls),
    and list any suspicious cases where name == ISO code.

    This helps detect codes that pycountry doesn't know and Comtrade didn't provide desc for.
    """
    rows = []
    for c in name_cols:
        if c not in df.columns:
            rows.append({"column": c, "warning": "missing column"})
            continue
        n = len(df)
        nulls = int(df[c].isna().sum())
        rows.append({"column": c, "rows": n, "nulls": nulls, "null_rate": nulls / n if n else None})

    out = pd.DataFrame(rows)

    # Identify where name looks like an ISO code (e.g., "WLD") — not necessarily wrong,
    # but a signal to create a manual mapping if you want it more readable.
    for iso_col, name_col in [("reporter", "reporter_name"), ("partner", "partner_name")]:
        if iso_col in df.columns and name_col in df.columns:
            suspicious = df.loc[df[name_col].astype(str) == df[iso_col].astype(str), iso_col].value_counts().head(50)
            if not suspicious.empty:
                s = suspicious.reset_index()
                s.columns = ["code", "count"]
                s["pair"] = f"{iso_col}->{name_col}"
                out = pd.concat([out, s], ignore_index=True)

    return out