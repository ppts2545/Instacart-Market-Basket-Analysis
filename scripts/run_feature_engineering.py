from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from instacart_quality import run_feature_engineering_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run feature engineering pipeline and write outputs to data/processed/features."
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Use full cleaned datasets instead of sample tables.",
    )
    parser.add_argument(
        "--snapshot-date",
        default="2015-07-01",
        help="Snapshot date used to back-calculate order_date (default: 2015-07-01).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_feature_engineering_pipeline(
        use_sample=not args.full,
        project_root=PROJECT_ROOT,
        snapshot_date=args.snapshot_date,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
