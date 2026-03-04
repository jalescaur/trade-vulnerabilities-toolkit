"""
src/taxonomy/basket.py
======================
Defines the AI infrastructure HS6 basket (v0.1) used in this project.

Goal:
- Keep ONLY the HS6 codes that we will analyze in the chapter.

Your basket:
Core / infrastructure-focused (still with a couple proxies that must be documented).

Important methodological note:
- HS codes are defined by the Harmonized System (WCO) and are revised periodically.
- UN Comtrade exports include a classification indicator (often `clCode` / HS version).
  We will audit this in the pipeline to ensure consistency across files.

References (for documentation / provenance):
- UN Statistics Division (UNSD) / UN Comtrade for trade data and classifications. 
- WCO HS background (HS 2012 tables, etc.). 
- UNSD conversion notes between HS editions (if you ever need crosswalks). 

Practical guidance for the chapter:
- Include this basket as "Table 1: Operational definition of AI infrastructure (HS6 basket)".
- For HS codes used as proxies (e.g., 850440, 841582), explicitly label them as proxies.
"""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(frozen=True)
class BasketItem:
    hs6: str
    desc: str
    layer: str          # compute / storage / network / optics / power / facility
    segment: str        # finer grouping if you want (can equal layer)
    proxy: bool         # True if "proxy" rather than uniquely AI infra
    note: str           # short rationale


# v0.1 — ONLY what listed as "Core"
AI_BASKET_V01 = [
    BasketItem("854231", "Integrated circuits: processors and controllers", "compute", "compute", False,
               "Direct compute core; widely used in AI-capable hardware."),
    BasketItem("854232", "Integrated circuits: memories", "compute", "memory", False,
               "Memory chips are a direct compute input and key bottleneck in AI infrastructure."),
    BasketItem("854239", "Integrated circuits: other (n.e.c.)", "compute", "ic_other", True,
               "Proxy: broad IC category; keep only if robust patterns persist with/without this code."),
    BasketItem("847150", "ADP units: processing units", "compute", "processing_units", False,
               "Direct hardware category for processing units in data/compute infrastructure."),
    BasketItem("847170", "ADP units: storage units", "storage", "storage_units", False,
               "Direct storage infrastructure category (critical for AI workloads)."),
    BasketItem("851762", "Communication apparatus: switching/routing; data transmission/regeneration",
               "network", "switching_routing", False,
               "Core networking gear enabling data center and backbone connectivity."),
    BasketItem("854470", "Optical fibre cables", "optics", "fiber_cables", False,
               "Physical layer backbone; core for data center and long-haul connectivity."),
    BasketItem("850440", "Electrical static converters", "power", "psu_ups_proxy", True,
               "Proxy: strong link to power supply/UPS infrastructure supporting compute facilities."),
    BasketItem("841582", "Air conditioning machines (not window/wall; with refrigerating unit)",
               "facility", "cooling_proxy", True,
               "Proxy: approximates cooling infrastructure relevant for data centers; HS includes broader uses."),
]


def basket_df_v01() -> pd.DataFrame:
    """Return basket v0.1 as a DataFrame suitable for joins."""
    return pd.DataFrame([{
        "hs6": i.hs6,
        "desc": i.desc,
        "layer": i.layer,
        "segment": i.segment,
        "proxy": i.proxy,
        "note": i.note,
        "basket_version": "v0.1",
    } for i in AI_BASKET_V01])