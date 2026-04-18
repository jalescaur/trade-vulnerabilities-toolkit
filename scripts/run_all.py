"""
scripts/run_all.py
------------------
End-to-end pipeline runner.

Usage:
  # Constructors only (build + audits + country names):
  python scripts/run_all.py --config configs/default.yaml

  # Constructors + analysis outputs (chapter tables + indexes + config export):
  python scripts/run_all.py --config configs/default.yaml --include-analysis

  # Skip the interactive country prompt (e.g. in automated/CI runs):
  python scripts/run_all.py --config configs/default.yaml --no-country-prompt

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

Country deep-dive (interactive prompt at start):
  9) 13_country_deep_dive.py  (runs last, after all other steps)
"""

from __future__ import annotations

import argparse
import os
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
    p.add_argument(
        "--no-country-prompt",
        action="store_true",
        help="Skip the interactive country/bloc selection prompt.",
    )
    p.add_argument(
        "--entities",
        default=None,
        help=(
            "Comma-separated list of countries/blocs for deep-dive analysis. "
            "Bypasses the interactive prompt. "
            "Example: --entities 'USA, China, ASEAN, European Union'"
        ),
    )
    p.add_argument(
        "--blocs",
        default="configs/blocs.yaml",
        help="Path to blocs.yaml (default: configs/blocs.yaml).",
    )
    return p.parse_args()


def run_step(script: str, config_path: str | None = None, extra_args: list | None = None) -> None:
    """
    Run a pipeline step as a subprocess.
    If config_path is provided, passes --config <path>.
    extra_args: additional CLI arguments to append.
    """
    cmd = [sys.executable, script]
    if config_path is not None:
        cmd += ["--config", config_path]
    if extra_args:
        cmd += extra_args

    log.info("Running: " + " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, capture_output=False)
    if r.returncode != 0:
        raise RuntimeError(f"Step failed ({script}) with code {r.returncode}")


def prompt_country_input() -> str:
    """
    Interactive prompt for country/bloc selection.

    Accepts:
    - Individual countries  : USA, Germany, Malaysia
    - Blocs / regions       : ASEAN, European Union, EU, NATO, G20, BRICS,
                              North America, Latin America, Southeast Asia, etc.
    - ISO3 codes            : CHN, BRA, SGP
    - Mixed                 : USA, ASEAN, Germany, Latin America

    Press Enter with no input to skip.
    """
    print()
    print("=" * 70)
    print("  COUNTRY & BLOC DEEP-DIVE ANALYSIS")
    print("=" * 70)
    print()
    print("  Enter countries and/or blocs for detailed trade analysis.")
    print("  Separate multiple entries with commas.")
    print()
    print("  Accepted formats (examples):")
    print("    Individual countries : USA, China, Malaysia, Germany")
    print("    ISO3 codes           : CHN, BRA, SGP, DEU")
    print("    Blocs / regions      : ASEAN, EU, European Union, NATO,")
    print("                           G20, BRICS, North America,")
    print("                           Latin America, Southeast Asia,")
    print("                           East Asia, Middle East, ...")
    print("    Mixed                : USA, ASEAN, Germany, Latin America")
    print()
    print("  Press Enter with no input to skip this step.")
    print()

    try:
        raw = input("  > Countries / blocs: ").strip()
    except (EOFError, KeyboardInterrupt):
        # Non-interactive or interrupted — skip gracefully
        print()
        raw = ""

    print()
    return raw


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    paths = cfg_paths(cfg)

    # ------------------------------------------------------------------ #
    # Collect country/bloc input BEFORE any pipeline step                  #
    # ------------------------------------------------------------------ #
    country_input: str = ""

    if args.entities:
        # Supplied via CLI flag — no prompt needed
        country_input = args.entities
        log.info(f"Country/bloc input (from --entities): {country_input}")
    elif not args.no_country_prompt:
        country_input = prompt_country_input()
        if country_input:
            log.info(f"Country/bloc input (from prompt): {country_input}")
        else:
            log.info("No country/bloc input provided — country deep-dive will be skipped.")
    else:
        log.info("Country prompt skipped (--no-country-prompt).")

    # ------------------------------------------------------------------ #
    # Ensure key directories exist                                         #
    # ------------------------------------------------------------------ #
    paths["processed_root"].mkdir(parents=True, exist_ok=True)
    (paths["processed_root"] / "intermediate_tables").mkdir(parents=True, exist_ok=True)
    paths["exploratory_dir"].mkdir(parents=True, exist_ok=True)
    paths["logs_dir"].mkdir(parents=True, exist_ok=True)

    log.info(f"Running pipeline with config: {Path(args.config).resolve()}")
    log.info(f"Raw root: {paths['raw_root']}")
    log.info(f"Intermediate dataset: {paths['intermediate_dataset']}")

    # ------------------------------------------------------------------ #
    # Constructor steps                                                    #
    # ------------------------------------------------------------------ #
    constructor_steps = [
        ("scripts/00_check_environment.py", True),
        ("scripts/01_build_dataset.py",     True),
        ("scripts/02_build_audits.py",       True),
        ("scripts/04_add_country_names.py",  True),
    ]

    for script, needs_config in constructor_steps:
        run_step(script, args.config if needs_config else None)

    # ------------------------------------------------------------------ #
    # Optional analysis steps                                              #
    # ------------------------------------------------------------------ #
    if args.include_analysis:
        log.info("Including analysis outputs (--include-analysis)")

        analysis_steps = [
            ("scripts/print_config_summary.py",              True),
            ("scripts/10_build_metrics_tables.py",            True),
            ("scripts/12_export_config_summary_to_outputs.py", True),
            ("scripts/11_build_chapter_index.py",             False),
        ]

        for script, needs_config in analysis_steps:
            run_step(script, args.config if needs_config else None)

    # ------------------------------------------------------------------ #
    # Country / bloc deep-dive (runs last)                                 #
    # ------------------------------------------------------------------ #
    if country_input and country_input.strip():
        log.info("Running country deep-dive analysis...")
        extra = [
            "--entities", country_input,
            "--blocs", args.blocs,
        ]
        run_step("scripts/13_country_deep_dive.py", args.config, extra_args=extra)
    else:
        log.info("Country deep-dive skipped.")

    log.info("All steps complete ✅")


if __name__ == "__main__":
    main()