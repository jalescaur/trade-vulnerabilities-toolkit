"""
scripts/run_all.py
------------------
End-to-end pipeline runner.

Usage:
  # Constructors only (build + audits + country names):
  python scripts/run_all.py --config configs/default.yaml

  # Constructors + analysis outputs (chapter tables + indexes + config export):
  python scripts/run_all.py --config configs/default.yaml --include-analysis

Steps (constructors):
1) 00_check_environment.py
2) 01_build_dataset.py
3) 02_build_audits.py
4) 04_add_country_names.py

Optional analysis steps (--include-analysis):
5) print_config_summary.py
6) 10_build_metrics_tables.py
7) 12_export_config_summary_to_outputs.py
8) 11_build_chapter_index.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from src.runtime_config import load_config, cfg_paths
from src.utils.logging import get_logger

log = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True, help="Path to YAML config file.")
    p.add_argument(
        "--include-analysis",
        action="store_true",
        help="If set, also generate chapter-ready tables/figures and indexes.",
    )
    return p.parse_args()


def run_step(script: str, config_path: str | None = None) -> None:
    """
    Run a pipeline step as a subprocess.
    If config_path is provided, passes --config <path>.
    """
    cmd = [sys.executable, script]
    if config_path is not None:
        cmd += ["--config", config_path]

    log.info(" ".join(cmd))
    r = subprocess.run(cmd, capture_output=False)
    if r.returncode != 0:
        raise RuntimeError(f"Step failed ({script}) with code {r.returncode}")


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    # Ensure key dirs exist
    paths["processed_root"].mkdir(parents=True, exist_ok=True)
    (paths["processed_root"] / "intermediate_tables").mkdir(parents=True, exist_ok=True)
    paths["exploratory_dir"].mkdir(parents=True, exist_ok=True)
    paths["logs_dir"].mkdir(parents=True, exist_ok=True)

    log.info(f"Running pipeline with config: {Path(args.config).resolve()}")
    log.info(f"Raw root: {paths['raw_root']}")
    log.info(f"Intermediate dataset: {paths['intermediate_dataset']}")

    # Constructors
    steps = [
        ("scripts/00_check_environment.py", True),
        ("scripts/01_build_dataset.py", True),
        ("scripts/02_build_audits.py", True),
        ("scripts/04_add_country_names.py", True),
    ]

    for script, needs_config in steps:
        run_step(script, args.config if needs_config else None)

    if args.include_analysis:
        log.info("Including analysis outputs (--include-analysis)")

        analysis_steps = [
            ("scripts/print_config_summary.py", True),
            ("scripts/10_build_metrics_tables.py", True),
            ("scripts/12_export_config_summary_to_outputs.py", True),
            ("scripts/11_build_chapter_index.py", False),
        ]

        for script, needs_config in analysis_steps:
            run_step(script, args.config if needs_config else None)

    log.info("All steps complete ✅")


if __name__ == "__main__":
    main()