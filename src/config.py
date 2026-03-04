"""
src/config.py
=============
Central configuration for paths and project conventions.

Why this exists:
- Reproducibility: One place to change folder locations and default settings.
- Readability: notebooks and scripts stay clean (no hardcoded paths everywhere).

Primary sources / references:
- UN Comtrade is the data source: https://comtrade.un.org/ (UN Statistics Division). 
  (In the final chapter, cite UN Comtrade and/or UNSD documentation for data provenance.)
- HS is maintained by the World Customs Organization (WCO) and used globally for goods classification. 
  (We only reference this as background in comments—no need to overcite in text.)

Note:
- The pipeline will *audit* classification/version fields when present in the raw files 
(e.g., clCode/classification).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# --------------------------------------------------------------------------------------
# Repository root and folder paths
# --------------------------------------------------------------------------------------

ROOT: Path = Path(__file__).resolve().parents[1]

DATA_DIR: Path = ROOT / "data"
DATA_RAW: Path = DATA_DIR / "raw"             # raw CSVs split by HS6 folders (your current structure)
DATA_EXTERNAL: Path = DATA_DIR / "external"   # mappings, crosswalks, etc.
DATA_PROCESSED: Path = DATA_DIR / "processed" # exploratory exports, intermediate artifacts

OUTPUTS_DIR: Path = ROOT / "outputs"
OUTPUT_TABLES: Path = OUTPUTS_DIR / "tables"  # chapter-ready tables (Excel + optional CSV)
OUTPUT_FIGURES: Path = OUTPUTS_DIR / "figures"  # chapter-ready figures (PDF/PNG)

LOGS_DIR: Path = OUTPUTS_DIR / "logs"         # optional: processing logs


def ensure_dirs() -> None:
    """Create expected directories if missing (safe to call repeatedly)."""
    for p in [
        DATA_EXTERNAL,
        DATA_PROCESSED,
        OUTPUT_TABLES,
        OUTPUT_FIGURES,
        LOGS_DIR,
    ]:
        p.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------------------
# Study window and defaults
# --------------------------------------------------------------------------------------

# Your study begins with "extensive adoption in 2021" and you have data through 2024.
YEAR_MIN: int = 2021
YEAR_MAX: int = 2024

# Canonical column names (after normalization). Keep these stable.
COL_YEAR = "year"
COL_REPORTER = "reporter"  # ISO3
COL_PARTNER = "partner"    # ISO3
COL_HS6 = "hs6"            # zero-padded string
COL_FLOW = "flow"          # Import/Export (if present; optional)
COL_VALUE = "value"        # numeric trade value (usually USD)

# Project taxonomy columns
COL_SEGMENT = "segment"
COL_LAYER = "layer"


# --------------------------------------------------------------------------------------
# Output conventions
# --------------------------------------------------------------------------------------

@dataclass(frozen=True)
class OutputNames:
    """
    Canonical filenames for outputs. Keeping names stable helps:
    - automate manuscript insertion
    - avoid "which version did we use?" confusion
    """
    audit_classification: str = "audit_classification_versions"
    audit_missingness: str = "audit_missingness"
    audit_duplicates: str = "audit_duplicates"
    audit_iso3: str = "audit_iso3_codes"


OUT = OutputNames()