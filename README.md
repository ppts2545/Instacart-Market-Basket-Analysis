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

4. Clean-only mode (keep only cleaned datasets)

python scripts/run_data_quality.py --clean-only

## Project Map (Recommended Working Structure)

Use this map to avoid mixing objectives and keep notebooks maintainable.

### Notebook Flow Index

01_Data_Understanding

- `01_data_overview.ipynb`: initial raw table inventory and quick profiling
- `02_data_understanding.ipynb`: deeper schema understanding and initial joins
- `04_data_quality.ipynb`: canonical raw-data quality checks
- `04b_processed_data_quality.ipynb`: processed artifact quality validation
- `05_feature_engineer.ipynb`: feature engineering experiments

02_Exploratory_Data_Analysis

- `00_eda_setup.ipynb`: shared EDA setup and merged base distribution overview
- `01_univariate_analysis.ipynb`: single-variable distribution checks
- `02a_customer_kpi_segments.ipynb`: customer KPI baseline and segmentation analysis
- `02b_customer_retention_clv.ipynb`: retention, churn, and CLV analysis
- `02c_customer_trends_diagnostics.ipynb`: trend deep dives and diagnostics
- `03_product_category_trends.ipynb`: product/category directional trends
- `04_customer_product_bridge.ipynb`: customer segment to category bridge

Legacy notebook retained for reference:

- `02_customer_behavior.ipynb`: original monolithic notebook before split

Rule of thumb:

- One notebook = one business question
- Shared logic (loading, merges, reusable feature steps) belongs in `src/`
- Notebook should focus on interpretation, not long ETL code

## Data Workflow (What To Do With Data)

Follow this fixed lifecycle:

1. Keep source files only in `data/raw`
2. Run `python scripts/run_data_quality.py`
3. Analyze from `data/processed/quality` only
4. Save visuals/tables to `reports/figures` and `reports/tables`

Data layer meaning:

- `data/raw`: immutable source inputs
- `data/interim`: optional temporary joins/feature drafts
- `data/processed/quality`: standardized cleaned tables + quality artifacts

### Notebook Data Loading Standard

Use package helper functions instead of hardcoded relative paths.

```python
from instacart_quality import load_eda_base

USE_SAMPLE = True
tables = load_eda_base(use_sample=USE_SAMPLE)

orders = tables["orders"]
order_products = tables["order_products_prior"]
products = tables["products"]
```

Benefits:

- no fragile `../../../` path logic
- same loading logic across all notebooks
- easy switch between sample and full data with one flag

## About Sample Data

The pipeline automatically creates **relational samples** that preserve referential integrity:
- Dimension tables (Products, Aisles, Departments) are filtered by what's referenced


## Output Artifacts
- column_missing.csv
- check_results.csv
- issue_register.csv
- imputation_log.csv
- missing_comparison_before_after.csv
- *_sample.csv for each table (relational samples with referential integrity)
- customer_cumulative_reorder_clean.csv (full feature table, local use)
- customer_cumulative_reorder_sample.csv and customer_cumulative_reorder_clean_sample.csv

In that mode, report files (table_profile, checks, issue_register, etc.) are skipped.

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
