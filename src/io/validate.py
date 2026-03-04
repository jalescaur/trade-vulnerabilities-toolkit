"""
src/io/validate.py
==================
Research-grade audits and sanity checks.

Why audits matter (methods logic, not "analysis"):
- Trade datasets are prone to:
  - mixed classification metadata (HS version / classification codes)
  - aggregate partners/reporters (e.g., WLD) or non-country entities
  - duplicates (especially when pulling from multiple files)
  - missingness in key columns
  - uneven coverage across years/codes

We keep these audits *separate* from analysis:
- audits document data quality and preprocessing decisions
- analysis computes substantive results (later)

Primary sources to cite in your chapter (not required for the code itself):
- UN Comtrade / UNSD documentation for trade data fields and classification metadata.
- HS background maintained by WCO/UNSD (for the concept of HS6 stability and revisions).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from src.config import (
    COL_YEAR, COL_REPORTER, COL_PARTNER, COL_HS6, COL_FLOW, COL_VALUE
)

# Loose ISO3 pattern check.
# NOTE: This does not validate against the ISO registry; it flags anomalies for inspection.
ISO3_RE = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True)
class AuditResult:
    """A standard container for audit outputs."""
    name: str
    rows: int
    details: pd.DataFrame


def is_plausible_iso3(x: str) -> bool:
    """Pattern-only ISO3 sanity check (AAA)."""
    return bool(ISO3_RE.match(str(x)))


# --------------------------------------------------------------------------------------
# Generic audits
# --------------------------------------------------------------------------------------

def audit_missingness(df: pd.DataFrame, cols: Iterable[str]) -> AuditResult:
    """
    Missingness table: counts and rates for selected columns.

    Tip:
    - For chapter methods appendix, it's often enough to report missingness for key fields:
      year, reporter, partner, hs6, value.
    """
    n = len(df)
    rows = []
    for c in cols:
        if c not in df.columns:
            rows.append({"column": c, "missing": n, "missing_rate": 1.0, "present": False})
            continue
        miss = int(df[c].isna().sum())
        rows.append({"column": c, "missing": miss, "missing_rate": miss / n if n else None, "present": True})
    out = pd.DataFrame(rows).sort_values(["missing_rate", "column"], ascending=[False, True])
    return AuditResult(name="audit_missingness", rows=len(out), details=out)


def audit_duplicates(df: pd.DataFrame, subset: list[str]) -> AuditResult:
    """
    Duplicate key audit.

    For trade data, a typical "record identity" might include:
    - year, reporter, partner, hs6, flow (or flowCode)

    However, the correct key depends on your extract.
    This audit does NOT delete duplicates; it quantifies and lists them.
    """
    # Only keep subset columns that exist to avoid hard failures.
    subset_existing = [c for c in subset if c in df.columns]
    if not subset_existing:
        return AuditResult("audit_duplicates", 0, pd.DataFrame([{
            "warning": "No subset columns exist in df; cannot audit duplicates."
        }]))

    dup_mask = df.duplicated(subset=subset_existing, keep=False)
    dup_rows = df.loc[dup_mask, subset_existing].copy()

    if dup_rows.empty:
        return AuditResult("audit_duplicates", 0, pd.DataFrame(columns=subset_existing + ["count"]))

    # Count duplicates by key
    counts = (
        dup_rows.value_counts()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    return AuditResult(name="audit_duplicates", rows=len(counts), details=counts)


def audit_iso3_codes(df: pd.DataFrame, cols=("reporter", "partner"), top_n: int = 50) -> AuditResult:
    """
    ISO3 anomaly audit (pattern-based).

    This will surface:
    - aggregates (e.g., WLD)
    - non-standard entities
    - malformed strings

    You can then decide in analysis whether to exclude aggregates.
    """
    rows = []
    for c in cols:
        if c not in df.columns:
            continue
        bad = df.loc[~df[c].apply(is_plausible_iso3), c].astype(str).value_counts().head(top_n)
        for code, count in bad.items():
            rows.append({"column": c, "code": code, "count": int(count)})

    out = pd.DataFrame(rows).sort_values(["column", "count"], ascending=[True, False])
    return AuditResult(name="audit_iso3_codes", rows=len(out), details=out)


# --------------------------------------------------------------------------------------
# Domain-specific audits (trade structure)
# --------------------------------------------------------------------------------------

def audit_year_coverage(df: pd.DataFrame) -> AuditResult:
    """Row counts and total values by year."""
    if COL_YEAR not in df.columns:
        return AuditResult("audit_year_coverage", 0, pd.DataFrame([{"warning": "Missing year column"}]))

    out = (
        df.groupby(COL_YEAR, as_index=False)
          .agg(rows=("year", "size"), total_value=(COL_VALUE, "sum"))
          .sort_values(COL_YEAR)
    )
    return AuditResult("audit_year_coverage", rows=len(out), details=out)


def audit_year_hs6_coverage(df: pd.DataFrame) -> AuditResult:
    """
    Coverage by year × HS6:
    - rows
    - total trade value

    This is helpful to verify every HS6 is present across the intended years.
    """
    need = {COL_YEAR, COL_HS6, COL_VALUE}
    if not need.issubset(df.columns):
        return AuditResult("audit_year_hs6_coverage", 0, pd.DataFrame([{
            "warning": f"Missing required columns: {sorted(list(need - set(df.columns)))}"
        }]))

    out = (
        df.groupby([COL_YEAR, COL_HS6], as_index=False)
          .agg(rows=(COL_HS6, "size"), total_value=(COL_VALUE, "sum"))
          .sort_values([COL_YEAR, "total_value"], ascending=[True, False])
    )
    return AuditResult("audit_year_hs6_coverage", rows=len(out), details=out)


def audit_flow_distribution(df: pd.DataFrame, flow_col_candidates=("flow", "flowDesc", "flowCode")) -> AuditResult:
    """
    Distribution of flows (Import/Export) if present.
    We keep this flexible because your dataset may store flow as text or code.
    """
    flow_col = None
    for c in flow_col_candidates:
        if c in df.columns:
            flow_col = c
            break

    if flow_col is None:
        return AuditResult("audit_flow_distribution", 0, pd.DataFrame([{"warning": "No flow column found"}]))

    out = (
        df[flow_col].astype(str).value_counts(dropna=False)
          .reset_index()
          .rename(columns={"index": "flow_value", flow_col: "count"})
    )
    out["share"] = out["count"] / out["count"].sum()
    return AuditResult("audit_flow_distribution", rows=len(out), details=out)


def audit_aggregate_flags(df: pd.DataFrame) -> AuditResult:
    """
    Audit aggregate indicators if present.

    Your raw schema includes:
    - isAggregate (boolean-ish)
    - isReported, isAggregate, isLeaf, aggrLevel, etc.

    After normalization we usually keep many original fields, so this audit can help
    decide whether to exclude aggregates from analysis.
    """
    candidates = [c for c in ["isAggregate", "aggrLevel", "isLeaf", "isReported"] if c in df.columns]
    if not candidates:
        return AuditResult("audit_aggregate_flags", 0, pd.DataFrame([{"warning": "No aggregate flag columns found"}]))

    rows = []
    for c in candidates:
        vc = df[c].astype(str).value_counts(dropna=False)
        for v, cnt in vc.items():
            rows.append({"field": c, "value": v, "count": int(cnt)})
    out = pd.DataFrame(rows).sort_values(["field", "count"], ascending=[True, False])
    out["share_within_field"] = out.groupby("field")["count"].transform(lambda s: s / s.sum())
    return AuditResult("audit_aggregate_flags", rows=len(out), details=out)