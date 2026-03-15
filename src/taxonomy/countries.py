"""
src/taxonomy/countries.py
=========================
Country name standardization (English).

Goal:
- Keep all entities in the dataset.
- Add explicit "full country name" columns for reporter and partner.

Strategy:
1) Prefer Comtrade-provided descriptors (reporterDesc/partnerDesc)
2) Fall back to ISO 3166-1 alpha-3 lookups via pycountry.
3) Apply manual overrides for known edge cases (Taiwan, Free Zones, etc.).
4) If all fails, keep the original code.
"""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
import pycountry

# Tradutor manual de anomalias e códigos agregados do UN Comtrade.
# Transforma as siglas em nomes descritivos em inglês (Padrão Acadêmico).
MANUAL_NAME_OVERRIDES: dict[str, str] = {
    "TWN": "Taiwan",
    "S19": "Taiwan",              # UN Comtrade usa S19 para Taiwan (Other Asia, nes)
    "W00": "World",               # World / Todos os países
    "WLD": "World",
    "_X":  "Unspecified",         # Não alocado / Sigilo comercial
    "XX":  "Special Categories",  # Categorias Especiais
    "X1":  "Bunkers",             # Abastecimento de navios/aeronaves
    "X2":  "Free Zones",          # Zonas Francas
    "E19": "Europe, nes",         # Europa, não especificada
    "F19": "Africa, nes",         # África, não especificada
    "A79": "Americas, nes",       # Américas, não especificadas
    "O19": "Oceania, nes",        # Oceania, não especificada
    "A59": "Asia, nes",           # Ásia, não especificada
    "XKX": "Kosovo",
    "ROM": "Romania",             # Código legado para Romênia
}

def iso3_to_english_name(iso3: str) -> str | None:
    if iso3 is None:
        return None
    code = str(iso3).upper()

    if code in MANUAL_NAME_OVERRIDES:
        return MANUAL_NAME_OVERRIDES[code]

    try:
        country = pycountry.countries.get(alpha_3=code)
        if country is None:
            return None
        return country.name
    except Exception:
        return None


def clean_comtrade_desc(desc: str, iso3: str | None = None) -> str | None:
    if desc is None:
        return None

    s = str(desc).strip()
    if not s or s.lower() == "nan":
        return None

    # Se a descrição do Comtrade vier cheia de códigos, aplicamos o override
    if iso3 is not None and str(iso3).upper() in MANUAL_NAME_OVERRIDES:
        return MANUAL_NAME_OVERRIDES[str(iso3).upper()]

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
    
    out = df.copy()

    # --- Reporter Name ---
    rep_desc = out[reporter_desc_col] if reporter_desc_col in out.columns else None
    out[reporter_name_col] = None

    if rep_desc is not None:
        out[reporter_name_col] = [
            clean_comtrade_desc(d, iso3=iso3) for d, iso3 in zip(rep_desc, out[reporter_iso_col])
        ]

    mask = out[reporter_name_col].isna()
    if mask.any():
        out.loc[mask, reporter_name_col] = out.loc[mask, reporter_iso_col].apply(iso3_to_english_name)

    mask = out[reporter_name_col].isna()
    out.loc[mask, reporter_name_col] = out.loc[mask, reporter_iso_col].astype(str)

    # --- Partner Name ---
    par_desc = out[partner_desc_col] if partner_desc_col in out.columns else None
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
    rows = []
    for c in name_cols:
        if c not in df.columns:
            rows.append({"column": c, "warning": "missing column"})
            continue
        n = len(df)
        nulls = int(df[c].isna().sum())
        rows.append({"column": c, "rows": n, "nulls": nulls, "null_rate": nulls / n if n else None})

    out = pd.DataFrame(rows)

    for iso_col, name_col in [("reporter", "reporter_name"), ("partner", "partner_name")]:
        if iso_col in df.columns and name_col in df.columns:
            suspicious = df.loc[df[name_col].astype(str) == df[iso_col].astype(str), iso_col].value_counts().head(50)
            if not suspicious.empty:
                s = suspicious.reset_index()
                s.columns = ["code", "count"]
                s["pair"] = f"{iso_col}->{name_col}"
                out = pd.concat([out, s], ignore_index=True)

    return out