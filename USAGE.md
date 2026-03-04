# Usage guide (trade-vulnerabilities-toolkit)

This repository is a **config-driven** pipeline for normalizing UN COMTRADE CSV exports and producing auditable intermediate datasets.

It does **not** ship any raw data. You provide CSVs locally.

---

## 1) Prepare your environment (pip)

```
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

## 2) Provide your raw COMTRADE CSVs

The pipeline supports two raw layouts, controlled by inputs.discovery_mode in the YAML config.

a) HS6 folder layout (discovery_mode: hs6_folders)

Use this when your files are split per HS6 code:

```
data/raw/
  854231/
    2021.csv
    2022.csv
  854232/
    2021.csv
  ...
```

Only HS6 folders listed in basket.hs6 will be discovered and processed.

b) Flat folder layout (discovery_mode: flat)

Use this when all CSVs are in one folder:

```
data/raw/
  export_1.csv
  export_2.csv
  ...
```

In this mode, the basket filtering happens after loading.

## 3) Create a config file

Start from: `configs/template.yaml` (blank, recommended) or `configs/default.yaml` (example)

Key fields: `schema.rename_map`

Maps raw column names → canonical names used by the software.

Canonical names expected by downstream steps:
- `year`, `reporter`, `partner`, `hs6`, `value`

Optional:
- `flow`
- `reporter_name_raw`, `partner_name_raw` (recommended for better labels)

### `basket.hs6`

A list of HS6 codes you want to analyze.

### `filters`

Set study window and minimal filters (e.g., `year_min`, `year_max`, `value_positive_only`).

## 4) Run the pipeline

Run end-to-end
`python scripts/run_all.py --config configs/your_config.yaml`

Run step-by-step

`python scripts/00_check_environment.py --config configs/your_config.yaml`
`python scripts/01_build_dataset.py --config configs/your_config.yaml`
`python scripts/02_build_audits.py --config configs/your_config.yaml`
`python scripts/04_add_country_names.py --config configs/your_config.yaml`

## 5) Outputs

#### Intermediate dataset (Parquet)

Written to:

- `data/processed/intermediate_tables/<intermediate_dataset_name>`
- plus an enriched version with country names: `data/processed/intermediate_tables/<stem>_country_names.parquet`

#### Audits (Excel)

Written to:

- `data/processed/exploratory_excels/audit_*.xlsx`

#### Logs

Written to:

- `outputs/logs/*.log`

## 6) Generate a config summary (for manuscript appendices)

`python scripts/print_config_summary.py --config configs/your_config.yaml`

This generates an Excel file summarizing:

- basket HS6 list + metadata
- year window and filters
- schema mapping (rename map)
- discovery settings

The output is written to:

`data/processed/exploratory_excels/config_summary.xlsx`
