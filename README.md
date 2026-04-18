# Trade Vulnerabilities Toolkit

**A configuration-driven pipeline for normalizing UN COMTRADE bilateral trade data and producing auditable trade vulnerability metrics.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19643339.svg)](https://doi.org/10.5281/zenodo.19643339)

---

## Overview

The Trade Vulnerabilities Toolkit is an open-source Python pipeline designed for researchers, analysts, and policymakers working with international merchandise trade data. It takes raw CSV exports from the [UN COMTRADE](https://comtrade.un.org/) database, normalizes them into a clean analytical dataset, and computes a comprehensive suite of trade and vulnerability metrics used in international trade economics, supply chain analysis, and geoeconomic research.

The toolkit was developed to support empirical research on trade concentration, dependency, and supply chain fragility in the context of AI infrastructure goods, but it is **general-purpose**: any basket of HS6 product codes can be analyzed by editing a single YAML configuration file.

In its current form, the toolkit includes a **configuration-driven end-to-end workflow**, a **unified pipeline orchestrator**, **region and bloc enrichment**, **publication-ready tabular exports**, **configuration receipts for reproducibility**, and **automated country/bloc deep-dive workbooks** for comparative geopolitical analysis.

### What It Does

1. **Ingests** raw COMTRADE CSV exports, whether organized by HS6 code folders or stored in a flat raw-data directory.
2. **Normalizes** column names, data types, trade flow labels, and product codes into a canonical schema.
3. **Audits** data quality, including missingness, duplicates, ISO3 anomalies, year coverage, flow distribution, and classification metadata.
4. **Enriches** records with standardized country names, geographic regions, and geopolitical bloc mappings.
5. **Computes trade metrics** such as market shares, concentration (HHI, CR3, CR5), growth (CAGR), volatility (CV), Revealed Comparative Advantage (Balassa RCA), intra-industry trade (Grubel-Lloyd), and export diversification (Shannon entropy).
6. **Computes vulnerability metrics** such as bilateral import exposure, dyadic asymmetry, top-supplier shock simulations, and supplier chokepoint scores.
7. **Generates country and bloc deep dives**, including entity-specific workbooks and comparative bilateral exposure matrices.
8. **Exports formatted outputs** as Excel tables, index files, audit spreadsheets, and configuration summaries ready for academic manuscripts, policy reports, or reproducible appendix documentation.

### What It Does Not Do

- It does not download data from COMTRADE automatically; users must obtain their own CSV exports.
- It does not perform causal inference or econometric estimation.
- It does not cover services trade, software, FDI, talent flows, or non-merchandise dimensions of technological power.
- It does not fully correct for re-exports, mirror-flow discrepancies, or confidential trade suppression; these issues are surfaced through audits and discussed as interpretive limitations.

---

## Methodological Foundations

The toolkit implements metrics that are standard in the international trade economics literature. All metrics operate on the canonical schema:

`year`, `reporter`, `partner`, `hs6`, `flow`, `value`

### Trade Metrics (`src/analysis/trade_metrics.py`)

| Metric                                 | What It Measures                                                                                                                           | Key Reference                                                                                                          |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| **Market Shares**                      | Relative weight of each product or country in trade flows                                                                                  | Standard                                                                                                               |
| **HHI (Herfindahl-Hirschman Index)**   | Overall concentration of supply or demand — sum of squared market shares (range: 1/N to 1.0)                                              | Hirschman, A. O. (1964). *The Paternity of an Index*. *American Economic Review*, 54(5), 761–762.                    |
| **CR*k* (Concentration Ratio)**        | Combined share of the top *k* exporters or suppliers                                                                                       | Bain, J. S. (1951). *Relation of Profit Rate to Industry Concentration*. *QJE*, 65(3), 293–324.                      |
| **CAGR (Compound Annual Growth Rate)** | Smoothed annualized growth over the study period                                                                                           | Standard                                                                                                               |
| **CV (Coefficient of Variation)**      | Trade value volatility relative to the mean (σ/μ)                                                                                          | Standard                                                                                                               |
| **RCA (Balassa Index)**                | Whether a country is disproportionately specialized in exporting a product relative to the world average (RCA > 1 = comparative advantage) | Balassa, B. (1965). *Trade Liberalisation and "Revealed" Comparative Advantage*. *The Manchester School*, 33(2), 99–123. |
| **IIT (Grubel-Lloyd Index)**           | Extent of simultaneous exports and imports within the same product category (0 = pure inter-industry; 1 = perfect intra-industry trade)   | Grubel, H. G., & Lloyd, P. J. (1975). *Intra-Industry Trade*. London: Macmillan.                                      |
| **Shannon Entropy**                    | Diversification of a country's export portfolio within the basket (higher = more diversified)                                              | Shannon, C. E. (1948). *A Mathematical Theory of Communication*. *Bell System Technical Journal*, 27(3), 379–423.    |

### Vulnerability Metrics (`src/analysis/vulnerability_metrics.py`)

| Metric                               | What It Measures                                                                              | Interpretation                                            |
| ------------------------------------ | --------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| **Import Dependence (Top*k* Share)** | Share of imports from the top 1, 3, or 5 suppliers per importer-product-year                  | High Top1 share = acute chokepoint vulnerability          |
| **Supplier HHI**                     | Concentration of an importer's supplier base                                                  | High HHI = over-reliance on few sources                   |
| **Bilateral Exposure**               | Share of Country A's imports sourced from Country B                                           | Measures the intensity of a specific bilateral dependency |
| **Dyadic Asymmetry**                 | Difference in exposure between two countries: Exposure(A←B) − Exposure(B←A)                   | Positive = A depends on B more than B depends on A        |
| **Shock Simulation**                 | Import capacity lost if the top supplier is removed                                           | Quantifies fragility to single-supplier disruption        |
| **Chokepoint Score**                 | Number of importers for which a supplier is the dominant source, and the total value at stake | Identifies systemically critical suppliers                |

### Deep-Dive and Comparative Outputs

The current pipeline also supports **Country & Bloc Deep Dive** analysis through a dedicated script and orchestrated execution path. These outputs extend the core descriptive metrics by isolating selected countries or blocs and generating:

- entity-specific summary workbooks,
- bilateral exposure matrices,
- side-by-side comparisons between major countries or geopolitical blocs,
- reproducible Excel artifacts suitable for appendices, technical notes, and manuscript supplements.

This makes the toolkit especially useful not only for general trade diagnostics, but also for focused geoeconomic comparison across strategic actors such as the United States, China, the European Union, ASEAN, or user-defined blocs.

---

## Repository Structure

```text
trade-vulnerabilities-toolkit/
│
├── configs/                          # YAML configuration files
│   ├── default.yaml                  # Default config for AI infrastructure basket
│   ├── blocs.yaml                    # Geopolitical bloc definitions for deep dives
│   └── template.yaml                 # Blank template for custom baskets
│
├── data/
│   ├── raw/                          # Raw COMTRADE CSVs (not included)
│   │   ├── 854231/                   # One folder per HS6 code (optional layout)
│   │   │   └── *.csv
│   │   ├── 854232/
│   │   └── ...
│   ├── processed/                    # Pipeline outputs
│   │   ├── intermediate_tables/      # Parquet files (normalized datasets)
│   │   └── exploratory_excels/       # Audit and diagnostic spreadsheets
│   └── external/                     # External mappings (if needed)
│
├── outputs/
│   ├── tables/                       # Chapter-ready Excel tables
│   ├── figures/                      # Publication-ready figures
│   ├── countries/                    # Country/bloc deep-dive workbooks
│   │   └── _comparative/             # Comparative bilateral outputs
│   └── logs/                         # Timestamped pipeline execution logs
│
├── scripts/                          # Pipeline step scripts
│   ├── 00_check_environment.py
│   ├── 01_build_dataset.py
│   ├── 02_build_audits.py
│   ├── 03_add_regions.py
│   ├── 04_add_country_names.py
│   ├── 10_build_metrics_tables.py
│   ├── 11_build_chapter_index.py
│   ├── 12_export_config_summary.py
│   ├── 13_country_deep_dive.py
│   ├── print_config_summary.py
│   └── run_all.py
│
├── src/                              # Source library
│   ├── config.py                     # Central path and column names
│   ├── runtime_config.py             # YAML config loader and validator
│   ├── analysis/
│   │   ├── trade_metrics.py          # Core trade metrics
│   │   ├── trade_tables.py           # Standardized trade tables
│   │   ├── vulnerability_metrics.py  # Supply chain vulnerability metrics
│   │   └── vulnerability_tables.py   # Standardized vulnerability tables
│   ├── io/
│   │   ├── discover.py               # File discovery (HS6 folders/flat)
│   │   ├── load.py                   # CSV loader with encoding fallbacks
│   │   ├── normalize.py              # Schema normalization
│   │   ├── validate.py               # Data quality audit functions
│   │   ├── export.py                 # Excel, Parquet, CSV
│   │   └── excel_format.py           # Formatted Excel output with styling
│   ├── taxonomy/
│   │   ├── basket.py
│   │   ├── countries.py              # ISO3 → country name handling
│   │   └── regions.py                # Geographic region and bloc mapping
│   ├── utils/
│   │   └── logging.py                # Project logger
│   └── viz/
│       ├── plots.py                  # Publication-ready figure generation
│       └── style_bw.py               # Black-and-white / grayscale styling
│
├── pyproject.toml                    # Project metadata and dependencies
├── requirements.txt                  # Pip requirements
├── run_pipeline.bat                  # Windows one-click pipeline runner
├── CITATION.cff                      # Citation metadata (CFF format)
├── LICENSE                           # MIT License
└── README.md                         # This file
```

---

## Getting Started

### Prerequisites

- **Python 3.10 or higher**
- **UN COMTRADE data**: you must download your own CSV exports from [UN COMTRADE](https://comtrade.un.org/). The toolkit does not include any trade data.

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_REPO/trade-vulnerabilities-toolkit.git
cd trade-vulnerabilities-toolkit
```

### Step 2: Create a Virtual Environment and Install Dependencies

```bash
python -m venv .venv

# Activate:
# Linux/macOS:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate

# Install the project (editable mode):
pip install -e .
```

This installs the project and its declared dependencies. In most environments, core packages will include tools such as `numpy`, `pandas`, `matplotlib`, `pyarrow`, `openpyxl`, `pycountry`, `PyYAML`, and `rich`, depending on the project metadata and lock/setup configuration.

### Step 3: Prepare Your Data

Download COMTRADE CSV exports for your HS6 codes of interest and place them under `data/raw/`.

The toolkit supports **two discovery modes**, controlled in the YAML configuration:

#### A. HS6 folder layout (`discovery_mode: hs6_folders`)

Use this when raw files are organized into one subfolder per HS6 code.

```text
data/raw/
├── 854231/
│   ├── comtrade_export_2021.csv
│   ├── comtrade_export_2022.csv
│   └── ...
├── 854232/
│   └── ...
└── ...
```

#### B. Flat folder layout (`discovery_mode: flat`)

Use this when all CSVs are stored together in the same folder and filtering happens after loading.

```text
data/raw/
├── export_1.csv
├── export_2.csv
└── export_3.csv
```

Each CSV should contain COMTRADE-style fields such as `period`, `reporterISO`, `partnerISO`, `flowDesc`, `cmdCode`, and `primaryValue`. These are mapped into the toolkit's canonical schema through the configuration file.

### Step 4: Configure

Edit `configs/default.yaml` to match your research setup. Key sections typically include:

```yaml
basket:
  hs6:
    - "854231"    # Processors and controllers
    - "854232"    # Memories
    # ... add your HS6 codes

filters:
  year_min: 2021
  year_max: 2024
  value_positive_only: true

schema:
  rename_map:
    period: "year"
    reporterISO: "reporter"
    partnerISO: "partner"
    flowDesc: "flow"
    cmdCode: "hs6"
    primaryValue: "value"
```

If your CSV columns have different names, adjust `schema.rename_map` accordingly.

Use `configs/template.yaml` as a starting point for new baskets. If you intend to use the Country & Bloc Deep Dive functionality, edit `configs/blocs.yaml` as well to define custom geopolitical blocs by ISO3 membership.

### Step 5: Run the Pipeline

The recommended entry point is the **unified orchestrator**:

#### Full pipeline (constructors + analysis + deep-dive prompt)

```bash
python scripts/run_all.py --config configs/default.yaml --include-analysis
```

This runs dataset construction, audits, enrichment, metrics, exports, and then triggers the interactive country/bloc deep-dive prompt.

#### Data preparation only

```bash
python scripts/run_all.py --config configs/default.yaml
```

This runs the constructor steps without the analysis and deep-dive components.

#### Headless / automated execution

To bypass interactive prompting:

```bash
# Skip the country deep-dive prompt entirely
python scripts/run_all.py --config configs/default.yaml --include-analysis --no-country-prompt

# Provide target entities directly
python scripts/run_all.py --config configs/default.yaml --include-analysis --entities "USA, China, ASEAN, European Union"
```

#### Windows one-click runner

```cmd
run_pipeline.bat configs\default.yaml
```

#### Individual steps

```bash
# Step 0: Verify environment and file discovery
python scripts/00_check_environment.py --config configs/default.yaml

# Step 1: Build normalized dataset
python scripts/01_build_dataset.py --config configs/default.yaml

# Step 2: Run data quality audits
python scripts/02_build_audits.py --config configs/default.yaml

# Step 3: Add geographic regions / bloc mappings
python scripts/03_add_regions.py --config configs/default.yaml

# Step 4: Add standardized country names
python scripts/04_add_country_names.py --config configs/default.yaml

# Step 5: Compute metrics and export tables
python scripts/10_build_metrics_tables.py --config configs/default.yaml

# Step 6: Build table index
python scripts/11_build_chapter_index.py

# Step 7: Export configuration summary / receipt
python scripts/12_export_config_summary.py --config configs/default.yaml

# Step 8: Run country or bloc deep dive
python scripts/13_country_deep_dive.py --config configs/default.yaml --entities "USA, China, ASEAN"
```

### Step 6: Review Outputs

After the pipeline completes, inspect the following locations:

| Location                              | Contents                                                                 |
| ------------------------------------- | ------------------------------------------------------------------------ |
| `outputs/tables/`                     | Chapter-ready Excel tables and table index files                         |
| `outputs/figures/`                    | Publication-ready figures (if figure scripts are enabled in your setup)  |
| `outputs/countries/`                  | Country/bloc deep-dive workbooks                                         |
| `outputs/countries/_comparative/`     | Comparative bilateral exposure outputs                                   |
| `outputs/logs/`                       | Timestamped execution logs for reproducibility                           |
| `data/processed/exploratory_excels/`  | Diagnostic audits and configuration receipts                             |
| `data/processed/intermediate_tables/` | Intermediate Parquet files                                               |

---

## Pipeline Architecture

The current toolkit is organized around a separation between **constructors** (data preparation and enrichment), **analysis** (metrics and final tables), and **deep-dive reporting** (entity-focused outputs).

```text
[Raw CSVs]
   ↓
00_check_environment
   ↓
01_build_dataset
   ↓
02_build_audits
   ↓
03_add_regions
   ↓
04_add_country_names
   ↓
[Intermediate Parquet + exploratory audits]
   ↓
10_build_metrics_tables
   ↓
11_build_chapter_index
   ↓
12_export_config_summary
   ↓
13_country_deep_dive (optional / prompt-driven / CLI-driven)
```

### Design Principles

- **Configuration-driven.** All key parameters — HS6 basket, column mappings, year range, discovery mode, paths, and bloc definitions — are specified in YAML rather than hardcoded into scripts.
- **Auditable.** Each major stage produces diagnostics or explicit outputs that allow the user to inspect missing values, dropped rows, naming anomalies, classification issues, and execution decisions.
- **Reproducible.** Given the same raw data and the same configuration, the pipeline is designed to reproduce the same outputs. Timestamped logs and exported configuration summaries support methodological traceability.
- **Modular.** Core metrics are implemented in reusable functions under `src/analysis/` and can be called independently in notebooks or custom scripts.
- **Transparent.** No trade data is distributed with the repository. Users remain responsible for sourcing and citing their own official data inputs.

---

## Outputs Reference

### Core Tables (`outputs/tables/`)

| File                                  | Description                                                                                                              | Key Metrics / Contents                  |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| `Table_00_MasterSummary.xlsx`         | Multi-tab summary workbook with explanations, global totals, top actors, vulnerability rankings, and resilience views   | Aggregates all metrics                  |
| `Table_01_GlobalTotals.xlsx`          | Total trade value by year and flow (Import/Export)                                                                      | Aggregate value                         |
| `Table_02_HS6Shares.xlsx`             | Share of each product segment within the total basket, by year and flow                                                 | Product composition                     |
| `Table_03_GlobalConcentration.xlsx`   | Global exporter concentration per product segment                                                                       | HHI, CR3, CR5, n_exporters              |
| `Table_04_ImporterDependency.xlsx`    | Importer-side supplier concentration per country-product-year                                                           | Top1_share, HHI_suppliers, top_supplier |
| `Table_05_GrowthVolatility.xlsx`      | Growth and volatility per product segment                                                                               | YoY growth, CAGR, CV                    |
| `Table_06_RCATopExporters.xlsx`       | Top exporters by Revealed Comparative Advantage per product segment                                                     | RCA (Balassa)                           |
| `Table_07_IntraIndustryTrade.xlsx`    | Intra-industry trade intensity per product segment                                                                      | Mean IIT, Median IIT                    |
| `Table_08_ExportDiversification.xlsx` | Export portfolio diversification per exporter                                                                           | Shannon entropy, n_products             |
| `Table_Index.xlsx`                    | Index of generated tables and workbook navigation aid                                                                   | Table registry                          |

### Diagnostic and Reproducibility Artifacts

| Location / File                                 | Description                                                                 |
| ----------------------------------------------- | --------------------------------------------------------------------------- |
| `data/processed/exploratory_excels/`            | Missingness reports, duplicates, ISO3 anomalies, coverage diagnostics       |
| `data/processed/exploratory_excels/*config*`    | Exported configuration summaries / receipts                                 |
| `outputs/logs/`                                 | Timestamped execution logs                                                  |

### Deep-Dive Outputs (`outputs/countries/`)

| Output Type                     | Description                                                                 |
| ------------------------------ | --------------------------------------------------------------------------- |
| Country workbook               | Entity-specific trade and vulnerability profile                             |
| Bloc workbook                  | Aggregated profile for predefined or custom geopolitical blocs              |
| Comparative bilateral workbook | Side-by-side exposure comparisons across selected entities                  |

### Figures (`outputs/figures/`)

If figure-generation scripts are enabled in the working version of the project, outputs may include publication-ready black-and-white / grayscale charts at print-friendly resolution. Typical examples may include:

- aggregate import/export flow evolution,
- HS6 segment trajectories,
- vulnerability rankings for selected country groups.

Because plotting workflows can vary across local project versions, users should confirm which figure scripts are active in their repository state.

---

## Adapting for Your Own Research

The toolkit is designed to be reused for any set of HS6 products. To analyze a different trade basket:

1. **Create a new config file** by copying `configs/template.yaml`.
2. **Replace the `basket.hs6` list** with your HS6 codes of interest.
3. **Download the corresponding COMTRADE data** and place it in `data/raw/`.
4. **Adjust the `schema.rename_map`** if your CSV columns differ from COMTRADE defaults.
5. **Choose your discovery mode** (`hs6_folders` or `flat`) according to your raw-data layout.
6. **Define bloc mappings** in `configs/blocs.yaml` if you want custom aggregate geopolitical comparisons.
7. **Run the pipeline** with `--config configs/your_config.yaml`.

No code changes should be required for ordinary reuse. The workflow is designed to be driven by configuration rather than script edits.

---

## Limitations and Caveats

Users should be aware of the following limitations:

1. **COMTRADE data quality.** Reporting lags, mirror-flow discrepancies between importers and exporters, and confidential trade suppression can affect results. The pipeline audits these issues but does not fully resolve them.
2. **HS6 product heterogeneity.** HS6 is the finest internationally comparable product classification, but it still aggregates heterogeneous goods. For example, HS6 854231 may include both advanced AI-relevant components and more general electronics.
3. **Re-export distortions.** Countries such as Hong Kong, Singapore, the Netherlands, and Belgium may function as transit hubs. Bilateral flows through these hubs may not reflect final production or final use.
4. **Goods trade only.** The toolkit analyzes merchandise trade. Software, cloud services, AI models, talent flows, and foreign direct investment are not captured.
5. **Descriptive indicators.** All metrics are descriptive and diagnostic. They should not be interpreted as causal evidence on their own.
6. **Bloc aggregation choices matter.** Custom bloc definitions can shape analytical outputs; users should document bloc membership decisions carefully.
7. **Proxy-product interpretation.** Some HS6 baskets may rely on proxy categories that mix AI-relevant items with broader product families. Results should therefore be interpreted with classification caution.

---

## Data Provenance and Ethics

- **Data source.** All trade data used with this toolkit must be obtained directly by the user from [UN COMTRADE](https://comtrade.un.org/) or equivalent official sources. No trade data is distributed with this repository.
- **COMTRADE terms.** Users are responsible for complying with COMTRADE's terms of use regarding data redistribution, licensing, and citation.
- **No personal data.** The toolkit processes aggregate country-level trade statistics only. No firm-level, individual-level, or personally identifiable information is involved.
- **Research transparency.** Because the toolkit exports diagnostics and configuration summaries, users are encouraged to archive these artifacts alongside manuscripts or replication packages whenever possible.

---

## Citation

If you use this toolkit in your research, please cite it as:

```text
Caur, J., Kreuz, J. (2026). Trade Vulnerabilities Toolkit: A configuration-driven pipeline for UN COMTRADE data normalization and trade vulnerability analysis (Version 0.1.0) [Software].
```

See `CITATION.cff` for machine-readable citation metadata. If you publish results produced with this toolkit, it is also good practice to cite the underlying methodological references listed above.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Authors

- **Jales Caur** — University of Brasília
- **Jônatas Kreuz** — University of Brasília

---

## Acknowledgments

This toolkit was developed as part of research on AI infrastructure trade vulnerabilities. The analytical methods implemented draw on established traditions in international trade economics, industrial organization, information theory, and geoeconomic analysis.

The authors thank the United Nations Statistics Division for maintaining the COMTRADE database, and the open-source Python ecosystem — including `pandas`, `numpy`, `matplotlib`, `openpyxl`, `pycountry`, and related tools — that made this workflow possible.

Generative AI was used in a supervised manner. The authors are not responsible for third-party interpretations of the processed data.
