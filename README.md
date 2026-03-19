# Instacart Market Basket Analysis

This repository includes a reusable, production-style data quality pipeline for Instacart raw data.

## Project Layout

- data/raw: source CSV files
- data/processed/quality: generated artifacts and cleaned tables
- notebook/01_data_understanding: analysis notebooks
- src/instacart_quality: reusable quality pipeline package
- config/quality_rules.json: quality rule definitions
- scripts/run_data_quality.py: one-command pipeline entrypoint

## Quick Start

1. Install dependencies

python -m pip install -r requirements.txt

2. Run quality pipeline

python scripts/run_data_quality.py

3. Optional: override paths

python scripts/run_data_quality.py --raw-dir data/raw --output-dir data/processed/quality --config config/quality_rules.json

## Output Artifacts

Pipeline generates:

- table_profile.csv
- column_missing.csv
- check_results.csv
- issue_register.csv
- imputation_log.csv
- missing_comparison_before_after.csv
- summary_kpi.csv
- *_clean.csv for each input table

## Customize Rules

Edit config/quality_rules.json to:

- add or remove PK/FK checks
- change range and allowed-set rules
- define missing-value imputation policies

## Recommended Next Step

Integrate scripts/run_data_quality.py into your future project as a quality gate before feature engineering or model training.
