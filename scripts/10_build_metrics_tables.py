"""
scripts/10_build_metrics_tables.py
==================================
Build chapter-ready metric tables (Excel) and the Master Summary.
Includes enriched theoretical explanations.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import pycountry

from src.runtime_config import load_config, cfg_paths
from src.io.excel_format import write_excel_table
from src.analysis.trade_tables import (
    table_global_totals,
    table_hs6_shares,
    table_global_exporter_concentration,
    table_importer_dependency,
    table_growth_volatility,
    table_rca_top,
    table_iit_summary,
    table_export_diversification,
)
from src.utils.logging import get_logger

log = get_logger(__name__)

G20_ISO = [
    "ARG", "AUS", "BRA", "CAN", "CHN", "FRA", "DEU", "IND", "IDN", "ITA", 
    "JPN", "KOR", "MEX", "RUS", "SAU", "ZAF", "TUR", "GBR", "USA", "EU2"
]

def get_country_name(iso3: str) -> str:
    if pd.isna(iso3):
        return ""
    try:
        overrides = {"TWN": "Taiwan", "S19": "Taiwan", "WLD": "World", "EU2": "European Union"}
        if iso3 in overrides:
            return overrides[iso3]
        return pycountry.countries.get(alpha_3=iso3).name
    except Exception:
        return str(iso3)

def inject_country_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    target_cols = ["reporter", "partner", "exporter", "importer", "country", "top_supplier"]
    for col in target_cols:
        if col in df.columns:
            df[f"{col}_name"] = df[col].apply(get_country_name)
            cols = list(df.columns)
            cols.remove(f"{col}_name")
            idx = cols.index(col)
            cols.insert(idx + 1, f"{col}_name")
            df = df[cols]
    return df

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, help="Path to YAML config.")
    return p.parse_args()


def build_master_summary(df: pd.DataFrame, out_path: Path):
    log.info("Building Table_00_MasterSummary.xlsx ...")
    
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        
        # TAB 1: Explanations - Grounded in the theoretical framework
        explanations = [
            {"Variable / Metric": "Market Share / Value", "Explanation": "Fundamental building block reflecting factor endowments and technological differences. Tracks competitive position, emerging actors, and structure of import dependence."},
            {"Variable / Metric": "CRk (Concentration Ratio)", "Explanation": "Originates in industrial organization (Bain, 1951). Quantifies market dominance of the top 'k' suppliers. High values signal oligopoly power, supply-chain vulnerability, and exposure to geopolitical weaponization."},
            {"Variable / Metric": "HHI (Herfindahl-Hirschman Index)", "Explanation": "Sum of squared market shares (Hirschman, 1964). Values > 0.25 indicate highly concentrated markets. Its convexity makes it highly sensitive to the presence of large players, serving as a key indicator of systemic monopoly/dependency."},
            {"Variable / Metric": "RCA (Revealed Comparative Advantage)", "Explanation": "Balassa Index (1965). Answers whether a country 'punches above its weight' in a product. RCA > 1 signifies over-representation relative to the global baseline, indicating structural competitive strength in AI infrastructure."},
            {"Variable / Metric": "Entropy", "Explanation": "Shannon Entropy (1948). Captures export portfolio diversification. Unlike HHI, it accounts for the entire distribution spread. Higher entropy reflects broader resilience against isolated demand shocks and terms-of-trade volatility."},
            {"Variable / Metric": "CAGR", "Explanation": "Compound Annual Growth Rate. Isolates long-run structural growth trajectories across products and countries from cyclical, short-term fluctuations."},
            {"Variable / Metric": "CV (Coefficient of Variation)", "Explanation": "Standard deviation divided by the mean. Functions as a proxy for market volatility and uncertainty. High CV indicates erratic trade behavior and susceptibility to price shocks."},
            {"Variable / Metric": "IIT (Grubel-Lloyd Index)", "Explanation": "Intra-Industry Trade (1975). Measures simultaneous export and import within the same category. Values approaching 1.0 indicate highly integrated mutual supply chains, typical of advanced economies trading differentiated varieties."},
            {"Variable / Metric": "G20 Filter", "Explanation": "Vulnerability rankings are isolated to major economies (G20) to provide policy-relevant insights into multipolar competition, avoiding mathematical distortions from micro-states."},
        ]
        
        pd.DataFrame(explanations).to_excel(writer, sheet_name="1_Explanations", index=False)

        # TAB 2: Global Totals (Wide Format para evitar erros de soma no Excel)
        g_tot = df.groupby(["year", "flow"])["value"].sum().unstack(fill_value=0).reset_index()
        g_tot.columns.name = None
        for col in ["Export", "Import"]:
            if col not in g_tot.columns:
                g_tot[col] = 0
        g_tot["Total_Trade (Exp+Imp)"] = g_tot["Export"] + g_tot["Import"]
        g_tot = g_tot[["year", "Export", "Import", "Total_Trade (Exp+Imp)"]]
        g_tot.to_excel(writer, sheet_name="2_Global_Totals", index=False)

        # TAB 3: HS6 Totals (Wide Format)
        hs6_tot = df.groupby(["year", "hs6", "flow"])["value"].sum().unstack(fill_value=0).reset_index()
        hs6_tot.columns.name = None
        for col in ["Export", "Import"]:
            if col not in hs6_tot.columns:
                hs6_tot[col] = 0
        hs6_tot["Total_Trade (Exp+Imp)"] = hs6_tot["Export"] + hs6_tot["Import"]
        hs6_tot = hs6_tot[["year", "hs6", "Export", "Import", "Total_Trade (Exp+Imp)"]]
        hs6_tot.to_excel(writer, sheet_name="3_HS6_Totals", index=False)

        # TAB 4: Top Actors Overall
        exporters = df[df.flow == "Export"].groupby("reporter")["value"].sum().reset_index()
        exporters["Country"] = exporters["reporter"].apply(get_country_name)
        exporters = exporters.sort_values("value", ascending=False).head(15)
        
        importers = df[df.flow == "Import"].groupby("reporter")["value"].sum().reset_index()
        importers["Country"] = importers["reporter"].apply(get_country_name)
        importers = importers.sort_values("value", ascending=False).head(15)
        
        top_actors = pd.concat([
            exporters.rename(columns={"reporter":"Exp_ISO", "value":"Total_Export_USD", "Country":"Top_Exporters"}).reset_index(drop=True),
            importers.rename(columns={"reporter":"Imp_ISO", "value":"Total_Import_USD", "Country":"Top_Importers"}).reset_index(drop=True)
        ], axis=1)
        top_actors.to_excel(writer, sheet_name="4_Top_Actors_Overall", index=False)

        # TAB 5: All Actors by Year
        actors_yr = df.groupby(["year", "flow", "reporter"])["value"].sum().reset_index()
        actors_yr["Country"] = actors_yr["reporter"].apply(get_country_name)
        actors_yr = actors_yr.sort_values(["year", "flow", "value"], ascending=[True, True, False])
        actors_yr.rename(columns={"reporter": "ISO3", "value": "Total_USD"}, inplace=True)
        actors_yr[["year", "flow", "ISO3", "Country", "Total_USD"]].to_excel(writer, sheet_name="5_Actors_By_Year", index=False)

        # TAB 6: Top 10 Actors by Year
        top10_yr = actors_yr.groupby(["year", "flow"]).head(10)
        top10_yr.to_excel(writer, sheet_name="6_Top10_By_Year", index=False)

        # TAB 7: Most Vulnerable (Filtered to G20)
        dep_df = table_importer_dependency(df)
        vuln = dep_df[dep_df["importer"].isin(G20_ISO)].groupby("importer").agg(
            Avg_Top1_Share=("Top1_share", "mean"),
            Avg_Supplier_HHI=("HHI_suppliers", "mean"),
            Unique_Suppliers_Used=("n_suppliers", "mean")
        ).reset_index()
        vuln["Country"] = vuln["importer"].apply(get_country_name)
        vuln = vuln.sort_values("Avg_Top1_Share", ascending=False)
        vuln = vuln[["importer", "Country", "Avg_Top1_Share", "Avg_Supplier_HHI", "Unique_Suppliers_Used"]]
        vuln.to_excel(writer, sheet_name="7_Most_Vulnerable_G20", index=False)

        # TAB 8: Most Resilient
        valid_exporters = exporters["reporter"].tolist()
        ent_df = table_export_diversification(df)
        strong = ent_df[ent_df["exporter"].isin(valid_exporters)].groupby("exporter").agg(
            Avg_Export_Entropy=("entropy", "mean"),
            Avg_Products_Exported=("n_products", "mean")
        ).reset_index()
        strong["Country"] = strong["exporter"].apply(get_country_name)
        strong = strong.sort_values("Avg_Export_Entropy", ascending=False).head(15)
        strong = strong.merge(exporters[["reporter", "value"]].rename(columns={"value": "Total_Export_USD"}), left_on="exporter", right_on="reporter")
        strong = strong[["exporter", "Country", "Total_Export_USD", "Avg_Export_Entropy", "Avg_Products_Exported"]]
        strong.to_excel(writer, sheet_name="8_Most_Resilient", index=False)

def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    in_path = paths["processed_root"] / "intermediate_tables" / f"{cfg['outputs']['intermediate_dataset_name'].replace('.parquet', '_country_names.parquet')}"
    if not in_path.exists():
        in_path = paths["intermediate_dataset"]

    df = pd.read_parquet(in_path)
    # W00 agora é filtrado direto na raiz (normalize.py), garantindo 100% de integridade no pipeline.
    
    log.info(f"Loaded analysis input: {in_path} | rows={len(df):,}, cols={len(df.columns)}")

    out_dir = Path("outputs") / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    build_master_summary(df, out_dir / "Table_00_MasterSummary.xlsx")

    # Tabelas Individuais com Notas Teóricas Aprofundadas
    t1 = inject_country_names(table_global_totals(df))
    write_excel_table(
        t1, out_dir / "Table_01_GlobalTotals.xlsx", "GlobalTotals", "Table 1: Global Trade Totals by Flow",
        note="Reflects the absolute market size (USD). Tracks structural trade shifts and global expansion of the AI infrastructure sector.",
        int_cols=["total_value"]
    )

    t2 = inject_country_names(table_hs6_shares(df))
    write_excel_table(
        t2, out_dir / "Table_02_HS6Shares.xlsx", "HS6Shares", "Table 2: HS6 Global Market Shares",
        note="Market share analysis. Identifies the proportional weight and relative importance of specific AI technology segments within the total basket.",
        percent_cols=["share_of_basket"]
    )

    t3 = inject_country_names(table_global_exporter_concentration(df))
    write_excel_table(
        t3, out_dir / "Table_03_GlobalConcentration.xlsx", "GlobalConc", "Table 3: Global Exporter Concentration (HHI & CRk)",
        note="Based on Hirschman (1964) and Bain (1951). HHI > 0.25 indicates highly concentrated origin markets, signaling global supply-chain vulnerability and oligopoly power.",
        percent_cols=["CR3", "CR5"], float_cols=["HHI"]
    )

    t4 = inject_country_names(table_importer_dependency(df))
    write_excel_table(
        t4, out_dir / "Table_04_ImporterDependency.xlsx", "ImpDep", "Table 4: Importer Supply Dependency (Chokepoints)",
        note="Assesses structural dependency at the nation-state level. High Top1_share reveals reliance on a single supplier, representing a critical geoeconomic chokepoint.",
        percent_cols=["Top1_share", "CR1", "CR3", "CR5"], float_cols=["HHI_suppliers"]
    )

    t5 = inject_country_names(table_growth_volatility(df))
    write_excel_table(
        t5, out_dir / "Table_05_GrowthVolatility.xlsx", "GrowthVol", "Table 5: HS6 Growth (CAGR) and Volatility (CV)",
        note="CAGR isolates long-run structural trends, while the Coefficient of Variation (CV) measures uncertainty, market instability, and exposure to short-term shocks.",
        percent_cols=["yoy_growth", "CAGR"], float_cols=["CV"]
    )

    t6 = inject_country_names(table_rca_top(df, top_n=15))
    write_excel_table(
        t6, out_dir / "Table_06_RCATopExporters.xlsx", "RCA", "Table 6: Revealed Comparative Advantage (RCA)",
        note="Balassa Index (1965). RCA > 1.0 indicates the country possesses a structural competitive advantage, exporting the technology at a higher rate than the global baseline.",
        float_cols=["RCA"]
    )

    t7 = inject_country_names(table_iit_summary(df))
    write_excel_table(
        t7, out_dir / "Table_07_IntraIndustryTrade.xlsx", "IIT", "Table 7: Intra-Industry Trade (Grubel-Lloyd)",
        note="Grubel & Lloyd (1975). Measures simultaneous two-way trade. Values near 1.0 show highly integrated mutual supply chains, typical of advanced economies.",
        float_cols=["mean_IIT", "median_IIT"]
    )

    t8 = inject_country_names(table_export_diversification(df))
    write_excel_table(
        t8, out_dir / "Table_08_ExportDiversification.xlsx", "ExportDiv", "Table 8: Export Portfolio Diversification (Entropy)",
        note="Shannon Entropy (1948). Higher values indicate a diversified export base, conferring broad resilience against single-product market shocks and terms-of-trade volatility.",
        float_cols=["entropy"]
    )

    log.info("Finished building all tables successfully.")

if __name__ == "__main__":
    main()