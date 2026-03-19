import argparse
from pathlib import Path

from .pipeline import run_data_quality_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Instacart data quality pipeline.")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing raw CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/quality"),
        help="Directory for quality artifacts and cleaned tables.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/quality_rules.json"),
        help="Path to quality rules config file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_data_quality_pipeline(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        config_path=args.config,
    )

    print("Data quality pipeline completed")
    print(f"Output directory: {result['output_dir']}")
    print(
        f"Checks: {result['pass_checks']}/{result['total_checks']} PASS "
        f"({result['pass_rate_pct']}%)"
    )
    print(
        f"Failures - critical: {result['critical_failures']}, "
        f"major: {result['major_failures']}"
    )
    print(f"Issue register rows: {result['issues_count']}")


if __name__ == "__main__":
    main()
