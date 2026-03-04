"""
scripts/00_check_environment.py
===============================
Config-driven environment and input sanity check.

Usage:
  python scripts/00_check_environment.py --config configs/default.yaml

Checks:
- Required imports
- Raw file discovery works according to discovery_mode
- Shows how many files will be loaded
"""

from __future__ import annotations

import argparse
from importlib import import_module

from src.runtime_config import load_config, cfg_paths
from src.io.discover import discover_raw_files
from src.utils.logging import get_logger

log = get_logger(__name__)


REQUIRED_IMPORTS = [
    "pandas",
    "numpy",
    "pyarrow",
    "openpyxl",
    "pycountry",
    "yaml",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, help="Path to YAML config.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    # Check imports
    for pkg in REQUIRED_IMPORTS:
        try:
            import_module(pkg)
            log.info(f"OK import: {pkg}")
        except Exception as e:
            log.error(f"FAILED import: {pkg} | {e}")
            raise

    raw_root = paths["raw_root"]
    mode = cfg["inputs"]["discovery_mode"]
    glob_pattern = cfg["inputs"]["glob"]
    allowed_hs6 = cfg["basket"]["hs6"]

    files = discover_raw_files(raw_root, discovery_mode=mode, glob_pattern=glob_pattern, allowed_hs6=allowed_hs6)

    log.info(f"Config: {args.config}")
    log.info(f"Raw root: {raw_root}")
    log.info(f"Discovery mode: {mode}")
    log.info(f"Glob pattern: {glob_pattern}")
    log.info(f"Basket HS6 count: {len(allowed_hs6)}")
    log.info(f"Discovered files: {len(files)}")

    if files:
        log.info(f"First file: {files[0]}")
        log.info(f"Last file:  {files[-1]}")
    else:
        log.warning("No files discovered. Check data/raw layout and config.inputs settings.")

    log.info("Environment check complete ✅")


if __name__ == "__main__":
    main()