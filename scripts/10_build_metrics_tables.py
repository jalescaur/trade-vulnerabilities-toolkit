"""
scripts/10_build_metrics_tables.py
==================================
Build chapter-ready metric tables (Excel formatted) + exploratory plots (PDF).

Usage:
  python scripts/10_build_metrics_tables.py --config configs/default.yaml

Outputs:
- Chapter tables (formatted): outputs/tables/*.xlsx
- Exploratory plots (compiled PDF): data/processed/exploratory_figures/metrics_exploratory.pdf
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

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
from src.analysis.vulnerability_tables import (
    table_import_dependence,
    table_bilateral_exposure_top,
    table_dyadic_asymmetry_top,
    table_shock_top,
    table_supplier_chokepoints,
)
from src.utils.logging import get_logger

log = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, help="Path to YAML config.")
    return p.parse_args()


def _pick_input_dataset(cfg: dict, paths: dict) -> Path:
    """
    Prefer the enriched dataset with country names if it exists:
      <stem>_country_names.parquet
    else fall back to intermediate dataset.
    """
    base = Path(cfg["outputs"]["intermediate_dataset_name"]).stem
    candidate = paths["processed_root"] / "intermediate_tables" / f"{base}_country_names.parquet"
    return candidate if candidate.exists() else paths["intermediate_dataset"]


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    out_tables = Path("outputs") / "tables"
    out_tables.mkdir(parents=True, exist_ok=True)

    processed_root = paths["processed_root"]
    exploratory_fig_dir = processed_root / "exploratory_figures"
    exploratory_fig_dir.mkdir(parents=True, exist_ok=True)

    in_path = _pick_input_dataset(cfg, paths)
    if not in_path.exists():
        raise FileNotFoundError(
            f"Input dataset not found: {in_path}\n"
            f"Run the constructor pipeline first:\n"
            f"  python scripts/run_all.py --config {args.config}"
        )

    df = pd.read_parquet(in_path)
    log.info(f"Loaded analysis input: {in_path} | rows={len(df):,}, cols={len(df.columns)}")

    # -----------------------
    # Build tables (core trade metrics)
    # -----------------------
    t1 = table_global_totals(df)
    t2 = table_hs6_shares(df)
    t3 = table_global_exporter_concentration(df)
    t4 = table_importer_dependency(df)
    t5 = table_growth_volatility(df)
    t6 = table_rca_top(df, top_n=10)
    t7 = table_iit_summary(df)
    t8 = table_export_diversification(df)
    t9  = table_import_dependence(df)
    t10 = table_bilateral_exposure_top(df, top_n=25)
    t11 = table_dyadic_asymmetry_top(df, top_n=25)
    t12 = table_shock_top(df, top_n=25)
    t13 = table_supplier_chokepoints(df, top_n=20)  # extra (chokepoint ranking)

    # -----------------------
    # Export "official" Excel outputs (chapter-ready)
    # -----------------------
    note_common = (
        "Computed from user-provided UN COMTRADE CSV exports after canonical normalization. "
        "Values are trade values as provided by COMTRADE (commonly in USD)."
    )

    write_excel_table(
        t1, out_tables / "Table_01_GlobalTotals.xlsx",
        sheet_name="GlobalTotals",
        title="Table 1. Global basket totals by year and flow",
        note=note_common,
        currency_cols=["total_value"],
        freeze_at="A3",
    )

    write_excel_table(
        t2, out_tables / "Table_02_HS6Shares.xlsx",
        sheet_name="HS6Shares",
        title="Table 2. HS6 shares of basket total by year and flow",
        note=note_common,
        currency_cols=["hs6_value", "basket_total"],
        percent_cols=["share_of_basket"],
        freeze_at="A3",
    )

    write_excel_table(
        t3, out_tables / "Table_03_GlobalExporterConcentration.xlsx",
        sheet_name="Concentration",
        title="Table 3. Global exporter concentration by HS6 and year (HHI, CR3, CR5)",
        note="Exporter concentration computed on Export flows: exporters = reporter. "
             "HHI and CRk are computed from exporter market shares.",
        percent_cols=["CR3", "CR5"],
        float_cols=["HHI"],
        int_cols=["n_exporters"],
        freeze_at="A3",
    )

    write_excel_table(
        t4, out_tables / "Table_04_ImporterDependency.xlsx",
        sheet_name="Dependency",
        title="Table 4. Importer supplier dependency by HS6 and year (Top1 share and supplier concentration)",
        note="Importer dependency computed on Import flows: importer = reporter, supplier = partner. "
             "Top1_share is the largest supplier share for a given importer-HS6-year.",
        percent_cols=["Top1_share", "CR1", "CR3", "CR5"],
        float_cols=["HHI_suppliers"],
        int_cols=["n_suppliers"],
        freeze_at="A3",
    )

    write_excel_table(
        t5, out_tables / "Table_05_GrowthVolatility.xlsx",
        sheet_name="GrowthVolatility",
        title="Table 5. HS6 growth and volatility (YoY growth, CAGR, coefficient of variation)",
        note="Growth/volatility computed from HS6 totals within the basket. "
             "CAGR/CV are computed over the available time window per HS6 and flow.",
        percent_cols=["yoy_growth", "CAGR"],
        float_cols=["CV"],
        currency_cols=["hs6_value"],
        freeze_at="A3",
    )

    write_excel_table(
        t6, out_tables / "Table_06_RCA_Top10.xlsx",
        sheet_name="RCA",
        title="Table 6. Revealed Comparative Advantage (Balassa RCA): top exporters per HS6",
        note="RCA computed from Export flows using the Balassa definition. "
             "This table reports the top 10 exporters by RCA for each HS6 and year.",
        float_cols=["RCA"],
        currency_cols=[],
        freeze_at="A3",
    )

    write_excel_table(
        t7, out_tables / "Table_07_IIT_Summary.xlsx",
        sheet_name="IIT",
        title="Table 7. Intra-industry trade (Grubel–Lloyd) summary by HS6 and year",
        note="IIT computed per country-HS6-year using Export and Import flows for the same reporter. "
             "This table summarizes mean and median IIT across countries with non-zero trade.",
        float_cols=["mean_IIT", "median_IIT"],
        int_cols=["n_countries"],
        freeze_at="A3",
    )

    write_excel_table(
        t8, out_tables / "Table_08_ExportDiversification.xlsx",
        sheet_name="Diversification",
        title="Table 8. Export diversification (entropy) across HS6 within the basket",
        note="Entropy computed from exporter HS6 export shares (higher entropy indicates more diversified export portfolio).",
        float_cols=["entropy"],
        int_cols=["n_products"],
        freeze_at="A3",
    )

    write_excel_table(
        t9, out_tables / "Table_09_ImportDependence_TopK.xlsx",
        sheet_name="ImportDependence",
        title="Table 9. Import dependence by HS6 and year (Top1/Top3/Top5 shares; supplier HHI)",
        note="Computed from Import flows: importer = reporter, supplier = partner. "
            "TopK_share sums the K largest supplier shares for each importer-HS6-year.",
        percent_cols=["Top1_share", "Top3_share", "Top5_share"],
        float_cols=["HHI_suppliers"],
        int_cols=["n_suppliers"],
        freeze_at="A3",
    )

    write_excel_table(
        t10, out_tables / "Table_10_BilateralExposure_Top.xlsx",
        sheet_name="Exposure",
        title="Table 10. Top bilateral import exposures by HS6 and year",
        note="Exposure(A<-B) = imports by A from B / total imports by A (within HS6 and year).",
        percent_cols=["exposure"],
        currency_cols=["importer_total", "bilateral_value"],
        freeze_at="A3",
    )

    write_excel_table(
        t11, out_tables / "Table_11_DyadicAsymmetry_Top.xlsx",
        sheet_name="Asymmetry",
        title="Table 11. Top asymmetric exposure dyads by HS6 and year",
        note="Asymmetry(A,B) = Exposure(A<-B) - Exposure(B<-A), where Exposure is computed from Import flows.",
        percent_cols=["A<-B", "B<-A", "asymmetry"],
        freeze_at="A3",
    )

    write_excel_table(
        t12, out_tables / "Table_12_Shock_RemoveTopSupplier.xlsx",
        sheet_name="ShockTop1",
        title="Table 12. Shock simulation: remove top supplier (largest potential import loss) by HS6 and year",
        note="For each importer-HS6-year, the shock loss share equals the top supplier share. "
            "This is a simple stress test proxy for chokepoint vulnerability.",
        percent_cols=["shock_loss_share"],
        currency_cols=["total_import", "top1_value", "post_shock_import"],
        freeze_at="A3",
    )

    write_excel_table(
        t13, out_tables / "Table_13_SupplierChokepoints.xlsx",
        sheet_name="Chokepoints",
        title="Table 13. Supplier chokepoint indicators by HS6 and year",
        note="Counts how often a supplier is the top-1 supplier across importers (and associated value/shares).",
        int_cols=["n_importers_top1"],
        currency_cols=["sum_top1_value"],
        percent_cols=["mean_top1_share"],
        freeze_at="A3",
    )

    log.info(f"Chapter tables written to: {out_tables.resolve()}")

    # -----------------------
    # Exploratory plots (compiled PDF into data/processed/)
    # -----------------------
    pdf_path = exploratory_fig_dir / "metrics_exploratory.pdf"
    with PdfPages(pdf_path) as pdf:
        # Plot 1: global totals by year-flow
        p = t1.pivot(index="year", columns="flow", values="total_value")
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        p.plot(ax=ax, marker="o")
        ax.set_title("Global basket totals by year and flow (exploratory)")
        ax.set_xlabel("Year")
        ax.set_ylabel("Trade value")
        ax.grid(True, linestyle=":", alpha=0.25)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Plot 2: HS6 share of basket (stack-ish via lines)
        # Pick one flow for readability (prefer Export if present)
        flow_choice = "Export" if "Export" in t2["flow"].unique() else t2["flow"].unique()[0]
        d = t2[t2["flow"] == flow_choice].copy()
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        for hs6, sub in d.groupby("hs6"):
            ax.plot(sub["year"], sub["share_of_basket"], marker="o", linewidth=1)
        ax.set_title(f"HS6 shares of basket total ({flow_choice}) — exploratory")
        ax.set_xlabel("Year")
        ax.set_ylabel("Share of basket")
        ax.grid(True, linestyle=":", alpha=0.25)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Plot 3: HHI exporter concentration distribution
        fig, ax = plt.subplots(figsize=(7.5, 4.5))
        ax.hist(t3["HHI"].dropna(), bins=20)
        ax.set_title("Distribution of exporter concentration (HHI) — exploratory")
        ax.set_xlabel("HHI")
        ax.set_ylabel("Count")
        ax.grid(True, linestyle=":", alpha=0.25)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Plot 4: Shock loss share distribution (Top1 supplier removal)
        if "shock_loss_share" in t12.columns:
            fig, ax = plt.subplots(figsize=(7.5, 4.5))
            ax.hist(t12["shock_loss_share"].dropna(), bins=20)
            ax.set_title("Shock loss share (remove top supplier) — exploratory")
            ax.set_xlabel("Shock loss share")
            ax.set_ylabel("Count")
            ax.grid(True, linestyle=":", alpha=0.25)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

        # Plot 5: Supplier chokepoint ranking (top suppliers by n_importers_top1)
        if "n_importers_top1" in t13.columns and "supplier" in t13.columns:
            # Use the most recent year available for a simple snapshot
            latest_year = t13["year"].max() if "year" in t13.columns else None
            snap = t13[t13["year"] == latest_year].copy() if latest_year is not None else t13.copy()
            snap = snap.sort_values("n_importers_top1", ascending=False).head(20)

            fig, ax = plt.subplots(figsize=(7.5, 4.5))
            ax.barh(snap["supplier"].astype(str), snap["n_importers_top1"])
            ax.set_title(f"Supplier chokepoints (top 20 by # importers as top-1) — {latest_year} — exploratory")
            ax.set_xlabel("# importers where supplier is top-1")
            ax.set_ylabel("Supplier")
            ax.grid(True, linestyle=":", alpha=0.25)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    log.info(f"Exploratory plots PDF written to: {pdf_path.resolve()}")
    log.info("Done ✅")


if __name__ == "__main__":
    main()