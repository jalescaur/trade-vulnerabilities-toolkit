"""
scripts/12_export_config_summary_to_outputs.py
==============================================
Copy config summary (exploratory) into outputs/tables/ as a chapter artifact.

Usage:
  python scripts/12_export_config_summary_to_outputs.py --config configs/default.yaml

Output:
  outputs/tables/Table_00_ConfigSummary.xlsx
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

from src.runtime_config import load_config, cfg_paths
from src.utils.logging import get_logger

log = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, help="Path to YAML config.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    # Ensure config summary exists
    config_summary = paths["exploratory_dir"] / "config_summary.xlsx"
    if not config_summary.exists():
        raise FileNotFoundError(
            f"Missing {config_summary}. Generate it first:\n"
            f"  python scripts/print_config_summary.py --config {args.config}"
        )

    out_dir = Path("outputs") / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "Table_00_ConfigSummary.xlsx"

    shutil.copyfile(config_summary, out_path)
    log.info(f"Copied config summary to: {out_path.resolve()}")
    log.info("Done ✅")


if __name__ == "__main__":
    main()