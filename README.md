# Instacart Market Basket Analysis

This repository includes a reusable, production-style data quality pipeline for Instacart raw data.

## Project Layout

- data/raw: source CSV files (large files ignored by git)
- data/interim: intermediate transformation outputs
- data/processed/quality: generated artifacts and cleaned tables
- data/external: third-party reference data
- notebooks: analysis notebooks grouped by workflow phase
- src/instacart_quality: reusable quality pipeline package
- configs/quality_rules.json: quality rule definitions
- scripts/run_data_quality.py: one-command pipeline entrypoint
- reports/figures and reports/tables: output-ready visuals and summary tables
- models: serialized models and metadata
- tests: validation and unit tests
- docs: project and data documentation

## Quick Start

1. Install dependencies

python -m pip install -r requirements.txt

2. Run quality pipeline (includes relational sampling)

python scripts/run_data_quality.py

3. Optional: override paths

python scripts/run_data_quality.py --raw-dir data/raw --output-dir data/processed/quality --config configs/quality_rules.json

## About Sample Data

The pipeline automatically creates **relational samples** that preserve referential integrity:

- Primary table (Orders) is sampled first (1000 rows by default)
- Child tables (Order_Products) are filtered by sampled order_ids
- Dimension tables (Products, Aisles, Departments) are filtered by what's referenced

**Result:** All foreign key constraints are maintained ✓

See [docs/RELATIONAL_SAMPLING.md](docs/RELATIONAL_SAMPLING.md) for details.

## Output Artifacts

Pipeline generates:

- table_profile.csv
- column_missing.csv
- check_results.csv
- issue_register.csv
- imputation_log.csv
- missing_comparison_before_after.csv
- summary_kpi.csv
- *_clean.csv for each input table (full cleaned data)
- *_sample.csv for each table (relational samples with referential integrity)
- customer_cumulative_reorder_clean.csv (full feature table, local use)
- customer_cumulative_reorder_sample.csv and customer_cumulative_reorder_clean_sample.csv

## Professional Git Workflow (Full Local, Sample Push)

Use full data locally for analysis, then regenerate and commit sample artifacts only.

1. Run full pipeline locally

python scripts/run_data_quality.py

2. Regenerate relational sample set + feature sample

python scripts/create_relational_samples.py --sample-size 1000

3. Stage code + notebooks + sample files

git add src scripts notebooks
git add data/raw/*sample*.csv
git add data/processed/**/*sample*.csv

4. Verify no full dataset is staged

git status --short

If full data was tracked in the past, untrack it once (keeps local files):

git rm -r --cached data/raw/*.csv data/processed/**/*.csv
git add data/raw/*sample*.csv data/processed/**/*sample*.csv

## Customize Rules

Edit configs/quality_rules.json to:

- add or remove PK/FK checks
- change range and allowed-set rules
- define missing-value imputation policies

## Recommended Next Step

Integrate scripts/run_data_quality.py into your future project as a quality gate before feature engineering or model training.
