# trade-vulnerabilities-toolkit

A **config-driven** Python workflow to ingest **UN COMTRADE** CSV exports, normalize them into a canonical dataset, and produce **auditable, reproducible** intermediate outputs for identifying **trade vulnerabilities and dependency patterns** (e.g., concentration, supplier dependence, chokepoints) from user-provided data.

This repository is intentionally **data-agnostic**: it does **not** ship any proprietary or large datasets. Instead, you provide COMTRADE CSV files locally, and the pipeline generates intermediate datasets and audits.

---

## What this software does

Given:
- a folder of COMTRADE CSV exports (your local data)
- a configuration file specifying:
  - which HS6 codes define your “infrastructure basket”
  - how to map CSV columns into canonical fields
  - study window and basic filters

The pipeline will:

1. Discover raw CSVs (either in HS6 subfolders or a flat folder).
2. Normalize raw columns into a canonical schema:
   - `year`, `reporter`, `partner`, `hs6`, `flow`, `value` (minimum)
3. Filter to **only** the HS6 codes in your basket and the chosen year range.
4. Produce reproducible **audits** (Excel) documenting:
   - classification fields (when present)
   - missingness
   - duplicates
   - ISO3 anomalies
   - year and HS6 coverage
   - flow distribution
   - aggregate flags (when present)
5. Add manuscript-friendly **English country names**:
   - `reporter_name`, `partner_name` (including a Taiwan override for readability)

---

## Data source

- **UN COMTRADE** (UN Statistics Division, UNSD)

You are responsible for obtaining the COMTRADE exports and placing them locally in `data/raw/` (see below).

---

## Quick start (pip)

### 1) Create and activate a virtual environment

```
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 2) Install dependencies

```
pip install -r requirements.txt
```

### 3) Put your COMTRADE CSVs in data/raw/

This software supports two input layouts (choose via config):

a) HS6 folder layout (recommended for baskets)

```
data/raw/
  854231/
    2021.csv
    2022.csv
  854232/
    2021.csv
    ...
```

b) Flat folder layout

```
data/raw/
  comtrade_export_1.csv
  comtrade_export_2.csv
  ...
```

### 4) Edit or copy a config file

Start from: `configs/default.yaml` (example basket and schema)

or:

`configs/template.yaml` (blank template)

### 5) Run the full pipeline

`python scripts/run_all.py --config configs/default.yaml`

---

## Outputs

Generated intermediates (not usually committed)

- `data/processed/intermediate_tables/<intermediate_dataset_name>`
- `data/processed/intermediate_tables/<intermediate_dataset_name_stem>_country_names.parquet`

Generated audits (Excel, regenerated)

- `data/processed/exploratory_excels/audit_*.xlsx`

Logs (regenerated)

- `outputs/logs/*.log`

## Configuration

All behavior is controlled by a YAML file.

Key sections:

- `inputs`: where raw data lives and how to discover it (hs6_folders or flat)
- `schema.rename_map`: map raw CSV columns to canonical fields
- `basket.hs6`: list of HS6 codes you want to analyze
- `filters`: year window and minimal filters
- `outputs`: where generated files are written

See:

`configs/default.yaml`
`configs/template.yaml`

## Country names and Taiwan

The pipeline adds: `reporter_name` and `partner_name`

Resolution order:
1. Prefer COMTRADE-provided descriptors (e.g., reporterDesc, partnerDesc) when present
2. Fallback to ISO 3166-1 alpha-3 lookups via pycountry
3. Manual overrides for edge cases (notably S19 → "Taiwan")
4. If all else fails, keep the original code (ensures no missing names)

Edit overrides in: `src/taxonomy/countries.py`

## Reproducibility notes

- This repository does not include raw data by default.
- All generated datasets/audits can be recreated using the same config file.
- Each run writes logs to outputs/logs/ documenting row counts and processing steps.

## Acknowledgements / references

- UN COMTRADE (UN Statistics Division) for trade data access and documentation.
- ISO 3166-1 alpha-3 via pycountry for fallback country name lookups.
- Harmonized System (HS) maintained by the World Customs Organization (WCO) as the product classification backbone.

Portions of the code and documentation were drafted with the assistance of a large language model under close human supervision; all methodological choices, data handling decisions, and final outputs were reviewed, tested, and validated by the authors.












































Code and reproducible workflow to map **vulnerabilities and dependency patterns in global AI infrastructure trade** using **UN COMTRADE** goods trade data (HS6), focused on the period **2021–2024**.

This repository is designed for **research transparency**:
- Raw inputs are kept separate from generated artifacts.
- All processing steps are scripted and logged.
- Outputs intended for the manuscript are stored in a dedicated folder.

---

## Project overview

### Research goal
Operationalize “AI infrastructure” as a **high-precision HS6 basket** (v0.1) and build a clean, reproducible dataset for downstream analysis (e.g., concentration, dependency, chokepoints).

### Data source
- **UN COMTRADE** (UN Statistics Division, UNSD) exports in CSV format.

### Basket scope (HS6, v0.1 — infrastructure)
Only the HS6 codes listed below are included in the analysis dataset:

- `841582` — Air conditioning machines (not window/wall; with refrigerating unit) *(proxy: facility cooling)*
- `847150` — ADP units: processing units
- `847170` — ADP units: storage units
- `850440` — Electrical static converters *(proxy: PSU/UPS)*
- `851762` — Communication apparatus: switching/routing; data transmission/regeneration
- `854231` — Integrated circuits: processors and controllers
- `854232` — Integrated circuits: memories
- `854239` — Integrated circuits: other (n.e.c.) *(proxy / broad IC category)*
- `854470` — Optical fibre cables

**Note on proxies:** Some HS6 items are used as strong proxies for data-center infrastructure (power and cooling). The codebase keeps these explicitly labeled (`proxy=True`) so results can be tested with/without them.

---

## Repository structure

ai-infrastructure-trade/
├─ data/
│ ├─ raw/ # raw COMTRADE exports (organized by HS6 folders)
│ ├─ external/ # optional mappings/crosswalks (if used later)
│ └─ processed/ # generated intermediates + exploratory Excel (ignored by git)
├─ outputs/
│ ├─ tables/ # manuscript-ready tables (Excel; may be committed)
│ ├─ figures/ # manuscript-ready figures (PDF/PNG; may be committed)
│ └─ logs/ # run logs (ignored by git)
├─ scripts/ # runnable pipeline steps
└─ src/ # reusable modules (loading/normalizing/audits/taxonomies)


---

## Data layout (required)

Raw CSVs must be organized like this:

data/raw/
841582/
*.csv
847150/
*.csv
...
854470/
*.csv


Each HS6 folder should contain **CSV files for 2021–2024** (one file per year is common, but not required).

### Expected CSV schema
This project assumes the COMTRADE export includes at least the following columns:

- `refYear`
- `reporterISO`, `partnerISO`
- `reporterDesc`, `partnerDesc` *(preferred English names)*
- `cmdCode`
- `flowDesc`
- `primaryValue`
- classification metadata fields (often present):
  - `classificationCode`, `classificationSearchCode`, `isOriginalClassification`

If your export uses different column names, adjust the mapping in:
- `src/io/normalize.py` (`DEFAULT_RENAME_MAP`)

---

## Installation (pip)

### 1) Create and activate a virtual environment (recommended)

```
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### 2) Install dependencies

```
pip install -r requirements.txt
```

## Reproducibility workflow

- Run the full constructor pipeline

From the repository root: 

```    
python scripts/run_all.py
```

This runs, in order:

`scripts/00_check_environment.py` — checks dependencies and raw folder structure
`scripts/01_build_dataset.py` — loads raw CSVs and builds the canonical dataset
`scripts/02_build_audits.py` — generates data-quality audits (Excel)
`scripts/04_add_country_names.py` — adds full English names for countries/areas

### What it gets after running

- Intermediate datasets (generated)

Stored in:

`data/processed/intermediate_tables/aiinfra_v01.parquet`
`data/processed/intermediate_tables/aiinfra_v01_country_names.parquet`

These are the recommended inputs for downstream analysis notebooks/scripts.

- Exploratory audits (Excel, generated)

Stored in:

`data/processed/exploratory_excels/audit_classification_versions.xlsx`
`data/processed/exploratory_excels/audit_missingness.xlsx`
`data/processed/exploratory_excels/audit_duplicates.xlsx`
`data/processed/exploratory_excels/audit_iso3_codes.xlsx`
`data/processed/exploratory_excels/audit_flow_distribution.xlsx`
`data/processed/exploratory_excels/audit_aggregate_flags.xlsx`
`data/processed/exploratory_excels/audit_country_name_coverage.xlsx`

- Logs (generated)

Each run writes a timestamped log file to: `outputs/logs/YYYYMMDD_HHMMSS.log`

## Country names (ISO3 → full English names, including Taiwan)

The pipeline adds:

`reporter_name` (English)
`partner_name` (English)

Resolution order:

1. Prefer COMTRADE-provided reporterDesc / partnerDesc (usually English, best coverage)
2. Fallback to ISO 3166-1 alpha-3 via pycountry
3. Apply manual overrides for edge cases (notably Taiwan → "Taiwan")

- If all else fails, keep the code (ensures no missing names), config: `src/taxonomy/countries.py`

## Outputs for the manuscript

- Exploratory vs final outputs (project policy)
- Exploratory Excel used during iteration → `data/processed/`
- Tables that will appear in the chapter/article → `outputs/tables/` (Excel)
- Figures that will appear in the chapter/article → `outputs/figures/` (PDF + PNG)
- This policy is enforced by using the centralized export helpers in `src/io/export.py`

## Notes on HS classification / versioning

- HS codes can change across revisions (editions). COMTRADE exports often include classification metadata such as: `classificationCode`, `classificationSearchCode`, `isOriginalClassification`
- This repository audits classification metadata and writes: `data/processed/exploratory_excels/audit_classification_versions.xlsx`
- If you discover mixed classification versions, you should resolve this before final analysis (e.g., restrict to a single HS edition or document conversion decisions).

## Acknowledgements / references

- UN COMTRADE (UN Statistics Division) for trade data access and documentation.
- ISO 3166-1 alpha-3 via pycountry for country name fallback lookups.
- Harmonized System (HS) maintained by the World Customs Organization (WCO) and used as the product classification backbone.

Portions of the codebase and documentation were drafted with the assistance of a large language model under close human supervision; all methodological choices, data handling decisions, and final wording were reviewed and validated by the authors.