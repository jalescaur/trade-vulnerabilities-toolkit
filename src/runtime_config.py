"""
src/runtime_config.py
---------------------
Generic runtime configuration loader for the pipeline.

Design:
- The project becomes a *general-purpose* pipeline that can be run on user-provided
  COMTRADE CSV exports, without bundling any data in the repo.
- Behavior is controlled by YAML config files in /configs.

This module only loads + validates configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class ConfigError(ValueError):
    """Raised when the runtime configuration is invalid."""


def _as_path(s: str) -> Path:
    return Path(s).expanduser().resolve()


def load_yaml(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ConfigError("Config root must be a YAML mapping/dict.")
    return data


def _require(d: Dict[str, Any], key: str, ctx: str = "") -> Any:
    if key not in d:
        raise ConfigError(f"Missing required key: {ctx}{key}")
    return d[key]


def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate minimal keys so downstream scripts can assume they exist.

    We keep validation lightweight and explicit (no heavy schema frameworks)
    to reduce dependencies and keep academic reproducibility simple.
    """
    _require(cfg, "inputs")
    _require(cfg, "basket")
    _require(cfg, "schema")
    _require(cfg, "filters")
    _require(cfg, "outputs")

    inputs = cfg["inputs"]
    basket = cfg["basket"]
    schema = cfg["schema"]
    filters = cfg["filters"]
    outputs = cfg["outputs"]

    _require(inputs, "raw_root", "inputs.")
    _require(inputs, "discovery_mode", "inputs.")
    _require(inputs, "csv_sep", "inputs.")
    _require(inputs, "glob", "inputs.")

    _require(basket, "hs6", "basket.")
    if not isinstance(basket["hs6"], list) or not basket["hs6"]:
        raise ConfigError("basket.hs6 must be a non-empty list of HS6 strings.")

    _require(schema, "rename_map", "schema.")
    if not isinstance(schema["rename_map"], dict) or not schema["rename_map"]:
        raise ConfigError("schema.rename_map must be a non-empty mapping.")

    _require(schema, "required_columns", "schema.")
    if not isinstance(schema["required_columns"], list) or not schema["required_columns"]:
        raise ConfigError("schema.required_columns must be a non-empty list.")

    _require(filters, "year_min", "filters.")
    _require(filters, "year_max", "filters.")
    _require(filters, "value_positive_only", "filters.")

    _require(outputs, "processed_root", "outputs.")
    _require(outputs, "intermediate_dataset_name", "outputs.")
    _require(outputs, "exploratory_excels_dir", "outputs.")
    _require(outputs, "logs_dir", "outputs.")

    # Normalize HS6 formatting (pad to 6 digits as strings)
    basket["hs6"] = [str(x).strip().zfill(6) for x in basket["hs6"]]

    return cfg


def load_config(path: str | Path) -> Dict[str, Any]:
    """Load + validate config and return a normalized dict."""
    cfg = load_yaml(path)
    return validate_config(cfg)


def cfg_paths(cfg: Dict[str, Any]) -> Dict[str, Path]:
    """
    Compute resolved Paths for I/O roots based on config.
    Kept here so scripts don’t duplicate path resolution logic.
    """
    raw_root = _as_path(cfg["inputs"]["raw_root"])
    processed_root = _as_path(cfg["outputs"]["processed_root"])
    exploratory_dir = _as_path(cfg["outputs"]["exploratory_excels_dir"])
    logs_dir = _as_path(cfg["outputs"]["logs_dir"])

    return {
        "raw_root": raw_root,
        "processed_root": processed_root,
        "exploratory_dir": exploratory_dir,
        "logs_dir": logs_dir,
        "intermediate_dataset": processed_root / "intermediate_tables" / cfg["outputs"]["intermediate_dataset_name"],
    }