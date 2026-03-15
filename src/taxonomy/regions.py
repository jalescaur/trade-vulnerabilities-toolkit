"""
src/taxonomy/regions.py
=======================
Mapeamento de regiões geográficas (Continentes/Macro-regiões).
"""

from __future__ import annotations

import pandas as pd
from src.utils.logging import get_logger

log = get_logger(__name__)

# Mapeamento estático básico (ISO3 -> Região)
REGION_MAP = {
    # Américas
    "USA": "North America", "CAN": "North America", "MEX": "North America",
    "BRA": "Latin America & Caribbean", "ARG": "Latin America & Caribbean",
    "CHL": "Latin America & Caribbean", "COL": "Latin America & Caribbean",
    "PER": "Latin America & Caribbean", "URY": "Latin America & Caribbean",
    "PRY": "Latin America & Caribbean", "BOL": "Latin America & Caribbean",
    "ECU": "Latin America & Caribbean", "VEN": "Latin America & Caribbean",
    
    # Europa
    "DEU": "Europe", "FRA": "Europe", "GBR": "Europe", "ITA": "Europe",
    "ESP": "Europe", "NLD": "Europe", "CHE": "Europe", "POL": "Europe",
    "SWE": "Europe", "BEL": "Europe", "AUT": "Europe", "NOR": "Europe",
    "PRT": "Europe", "GRC": "Europe", "IRL": "Europe", "CZE": "Europe",
    "HUN": "Europe", "ROU": "Europe", "RUS": "Europe", "UKR": "Europe",
    
    # Ásia / Pacífico
    "CHN": "Asia Pacific", "JPN": "Asia Pacific", "KOR": "Asia Pacific",
    "IND": "Asia Pacific", "AUS": "Asia Pacific", "NZL": "Asia Pacific",
    "SGP": "Asia Pacific", "MYS": "Asia Pacific", "THA": "Asia Pacific",
    "IDN": "Asia Pacific", "VNM": "Asia Pacific", "PHL": "Asia Pacific",
    "TWN": "Asia Pacific", "HKG": "Asia Pacific",
    
    # África
    "ZAF": "Africa", "NGA": "Africa", "EGY": "Africa", "MAR": "Africa",
    "DZA": "Africa", "KEN": "Africa", "ETH": "Africa", "GHA": "Africa",
    "AGO": "Africa",
    
    # Oriente Médio
    "SAU": "Middle East", "ARE": "Middle East", "ISR": "Middle East",
    "TUR": "Middle East", "QAT": "Middle East",
}

def get_region_name(iso3: str) -> str:
    if pd.isna(iso3):
        return "Unknown"
    return REGION_MAP.get(str(iso3).upper(), "Other")

def add_regions(df: pd.DataFrame, reporter_col="reporter", partner_col="partner") -> pd.DataFrame:
    df = df.copy()
    if reporter_col in df.columns:
        df["reporter_region"] = df[reporter_col].apply(get_region_name)
    if partner_col in df.columns:
        df["partner_region"] = df[partner_col].apply(get_region_name)
    return df

def audit_region_coverage(df: pd.DataFrame, col: str, top_n: int = 50) -> pd.DataFrame:
    region_col = f"{col}_region"
    if region_col not in df.columns:
        return pd.DataFrame()
    unmapped = df[df[region_col].isin(["Other", "Unknown"])].copy()
    if unmapped.empty:
        return pd.DataFrame(columns=["iso3", "count", "share_of_unmapped"])
    counts = unmapped[col].value_counts().reset_index()
    counts.columns = ["iso3", "count"]
    counts["share_of_unmapped"] = counts["count"] / counts["count"].sum()
    return counts.head(top_n)