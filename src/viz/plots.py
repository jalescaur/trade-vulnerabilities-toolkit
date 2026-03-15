"""
src/viz/plots.py
================
Generates didactic visualizations for the manuscript.
"""

import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pycountry

from src.runtime_config import load_config, cfg_paths
from src.viz.style_bw import set_bw_style, HATCHES, GRAY_COLORS
from src.analysis.vulnerability_metrics import import_dependence_topk
from src.utils.logging import get_logger

log = get_logger(__name__)

G20_ISO = [
    "ARG", "AUS", "BRA", "CAN", "CHN", "FRA", "DEU", "IND", "IDN", "ITA", 
    "JPN", "KOR", "MEX", "RUS", "SAU", "ZAF", "TUR", "GBR", "USA", "EU2"
]

def get_country_name(iso3: str) -> str:
    """Converte ISO3 para o nome do país em inglês."""
    if pd.isna(iso3):
        return ""
    try:
        overrides = {"TWN": "Taiwan", "S19": "Taiwan", "WLD": "World", "EU2": "European Union"}
        if iso3 in overrides:
            return overrides[iso3]
        return pycountry.countries.get(alpha_3=iso3).name
    except Exception:
        return str(iso3)

def format_billions(x, pos):
    """Formats axis values as Billions (e.g., 50_000_000_000 -> 50B)"""
    if x == 0:
        return "0"
    return f"{x * 1e-9:.0f}B"

def plot_global_flows(df: pd.DataFrame, out_dir: Path):
    """Gráfico 1: Fluxo de Importação vs Exportação por Ano."""
    log.info("Generating Global Flows plot...")
    
    g = df.groupby(["year", "flow"])["value"].sum().unstack(fill_value=0)
    for f in ["Import", "Export"]:
        if f not in g.columns:
            g[f] = 0.0
            
    years = g.index.astype(int)
    imports = g["Import"]
    exports = g["Export"]

    fig, ax = plt.subplots(figsize=(8, 5))
    bar_width = 0.35
    x = np.arange(len(years))

    ax.bar(x - bar_width/2, imports, bar_width, label="Import", 
           color=GRAY_COLORS[1], edgecolor='black', hatch=HATCHES[0])
    ax.bar(x + bar_width/2, exports, bar_width, label="Export", 
           color=GRAY_COLORS[3], edgecolor='black', hatch=HATCHES[1])

    ax.set_ylabel("Total Trade Value (USD)")
    
    # Estética estilo Excel: Título acima, legenda centralizada embaixo dele
    ax.set_title("Global AI Infrastructure Trade Volume", fontweight='bold', pad=40)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False)
    
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.yaxis.set_major_formatter(FuncFormatter(format_billions))
    
    # Ajusta o topo para a legenda não cortar
    plt.subplots_adjust(top=0.85)

    out_path = out_dir / "Fig_01_GlobalFlows.png"
    fig.savefig(out_path)
    plt.close(fig)


def plot_hs6_evolution(df: pd.DataFrame, out_dir: Path):
    """Gráfico 2: Evolução de TODOS os produtos da cesta por ano (Formato Retrato)."""
    log.info("Generating HS6 Evolution plot...")
    
    g = df[df["flow"] == "Export"].groupby(["year", "hs6"])["value"].sum().reset_index()
    if g.empty:
        return

    all_hs6 = g.groupby("hs6")["value"].sum().sort_values(ascending=False).index
    
    fig, ax = plt.subplots(figsize=(6, 8))
    
    markers = ['o', 's', '^', 'D', 'v', 'p', '*', 'X', '>']
    lines = ['-', '--', '-.', ':', '-', '--', '-.', ':', '-']
    
    for idx, hs6 in enumerate(all_hs6):
        sub = g[g["hs6"] == hs6].sort_values("year")
        ax.plot(sub["year"], sub["value"], 
                marker=markers[idx % len(markers)], 
                linestyle=lines[idx % len(lines)], 
                color="black", label=f"HS {hs6}", markersize=6, linewidth=1.5)

    ax.set_ylabel("Export Value (USD)")
    ax.set_title("Growth of AI Infrastructure Segments", fontweight='bold', pad=20)
    ax.set_xticks(g["year"].unique())
    
    ax.legend(title="Product Segment", loc="upper left", bbox_to_anchor=(1.02, 1.0))
    ax.yaxis.set_major_formatter(FuncFormatter(format_billions))

    out_path = out_dir / "Fig_02_HS6Evolution.png"
    fig.savefig(out_path)
    plt.close(fig)


def plot_vulnerability_g20(df: pd.DataFrame, out_dir: Path):
    """Gráfico 3: Dependência média (Top 1 Share) do G20."""
    log.info("Generating G20 Vulnerability plot...")
    
    dep_df = import_dependence_topk(df, k_list=[1])
    if dep_df.empty:
        return
        
    g20_dep = dep_df[dep_df["importer"].isin(G20_ISO)].groupby("importer")["Top1_share"].mean()
    g20_dep.index = g20_dep.index.map(get_country_name)
    g20_dep = g20_dep.sort_values(ascending=True)
    
    fig, ax = plt.subplots(figsize=(7, 8))
    
    colors = [GRAY_COLORS[2] if val <= 0.5 else GRAY_COLORS[0] for val in g20_dep.values]
    
    ax.barh(g20_dep.index, g20_dep.values, color=colors, edgecolor='black', height=0.7)
    ax.axvline(0.5, color='black', linestyle='--', linewidth=1.5)
    
    ax.set_xlabel("Share of Imports from Top 1 Supplier")
    ax.set_title("Vulnerability to Supply Chain Chokepoints\n(Average Top 1 Supplier Share, G20)", fontweight='bold', pad=20)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: '{:.0%}'.format(x)))
    
    # Legenda explicativa para a linha de 50%
    from matplotlib.lines import Line2D
    custom_lines = [Line2D([0], [0], color='black', linestyle='--', lw=1.5)]
    ax.legend(custom_lines, ['Critical Vulnerability (>50% from a single origin)'], loc='lower right', frameon=False)

    out_path = out_dir / "Fig_03_VulnerabilityG20.png"
    fig.savefig(out_path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    in_path = paths["processed_root"] / "intermediate_tables" / f"{cfg['outputs']['intermediate_dataset_name'].replace('.parquet', '_country_names.parquet')}"
    if not in_path.exists():
         in_path = paths["processed_root"] / "intermediate_tables" / cfg['outputs']['intermediate_dataset_name']
         
    df = pd.read_parquet(in_path)
    log.info(f"Loaded {len(df)} rows for visualizations.")

    # CRÍTICO: Remove o 'Mundo' (W00/WLD) da base de parceiros para não duplicar valores
    # nem distorcer a matemática de vulnerabilidade.
    df = df[~df["partner"].isin(["W00", "WLD"])].copy()

    out_dir = Path("outputs/figures")
    out_dir.mkdir(parents=True, exist_ok=True)

    set_bw_style()

    plot_global_flows(df, out_dir)
    plot_hs6_evolution(df, out_dir)
    plot_vulnerability_g20(df, out_dir)
    
    log.info(f"All figures saved to {out_dir.resolve()}")

if __name__ == "__main__":
    main()