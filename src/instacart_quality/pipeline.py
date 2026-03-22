import json
from pathlib import Path
from typing import Any

import pandas as pd

from .features import run_feature_engineering_pipeline


RAW_FILES = {
    "orders": "orders.csv",
    "order_products_prior": "order_products__prior.csv",
    "order_products_train": "order_products__train.csv",
    "products": "products.csv",
    "aisles": "aisles.csv",
    "departments": "departments.csv",
}


def build_customer_cumulative_reorder_feature(
    orders_df: pd.DataFrame,
    order_products_prior_df: pd.DataFrame,
) -> pd.DataFrame:
    """Create cumulative reorder-per-customer feature on prior-order line items."""
    feature_df = order_products_prior_df.merge(
        orders_df[["order_id", "user_id", "order_number"]],
        on="order_id",
        how="left",
    )
    feature_df = feature_df.sort_values(
        ["user_id", "order_number", "add_to_cart_order"]
    ).reset_index(drop=True)
    feature_df["cumulative_reorder_per_customer"] = (
        feature_df.groupby("user_id")["reordered"].cumsum()
    )
    return feature_df[
        [
            "order_id",
            "user_id",
            "order_number",
            "product_id",
            "add_to_cart_order",
            "reordered",
            "cumulative_reorder_per_customer",
        ]
    ]


def load_rules(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_tables(raw_dir: Path) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for table, file_name in RAW_FILES.items():
        path = raw_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")
        tables[table] = pd.read_csv(path)
    return tables


def profile_tables(table_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, df in table_dict.items():
        rows.append(
            {
                "table": name,
                "rows": int(df.shape[0]),
                "cols": int(df.shape[1]),
                "memory_mb": round(float(df.memory_usage(deep=True).sum() / 1024**2), 2),
                "duplicate_rows": int(df.duplicated().sum()),
                "missing_cells": int(df.isna().sum().sum()),
                "missing_pct_cells": round(float((df.isna().sum().sum() / df.size) * 100), 4),
            }
        )
    return pd.DataFrame(rows).sort_values(["missing_cells", "duplicate_rows"], ascending=False)


def column_missing(table_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    for table_name, df in table_dict.items():
        missing = df.isna().sum()
        for col, miss_count in missing.items():
            miss_count = int(miss_count)
            if miss_count > 0:
                records.append(
                    {
                        "table": table_name,
                        "column": col,
                        "missing_count": miss_count,
                        "missing_pct": round(float((miss_count / len(df)) * 100), 4),
                    }
                )
    if not records:
        return pd.DataFrame(columns=["table", "column", "missing_count", "missing_pct"])
    return pd.DataFrame(records).sort_values(["missing_pct", "missing_count"], ascending=False)


def check_pk_unique(df: pd.DataFrame, table_name: str, key_col: str, severity: str) -> dict[str, Any]:
    non_null_count = int(df[key_col].notna().sum())
    unique_non_null = int(df[key_col].nunique(dropna=True))
    pass_flag = bool(df[key_col].is_unique and non_null_count == len(df))
    return {
        "check_type": "PK_UNIQUENESS",
        "table": table_name,
        "column": key_col,
        "status": "PASS" if pass_flag else "FAIL",
        "invalid_count": int(len(df) - unique_non_null),
        "severity": severity,
        "detail": f"non_null={non_null_count}, unique_non_null={unique_non_null}, rows={len(df)}",
    }


def check_fk_coverage(
    child_df: pd.DataFrame,
    child_table: str,
    child_col: str,
    parent_df: pd.DataFrame,
    parent_table: str,
    parent_col: str,
    severity: str,
) -> dict[str, Any]:
    valid_mask = child_df[child_col].isin(parent_df[parent_col])
    invalid_count = int((~valid_mask).sum())
    coverage = float(valid_mask.mean() * 100)
    return {
        "check_type": "FK_COVERAGE",
        "table": child_table,
        "column": child_col,
        "status": "PASS" if invalid_count == 0 else "FAIL",
        "invalid_count": invalid_count,
        "severity": severity,
        "detail": f"{child_table}.{child_col} in {parent_table}.{parent_col} = {coverage:.4f}%",
    }


def check_range(
    df: pd.DataFrame,
    table_name: str,
    col: str,
    min_val: float,
    max_val: float,
    severity: str,
) -> dict[str, Any]:
    invalid_mask = ~df[col].between(min_val, max_val)
    invalid_count = int(invalid_mask.sum())
    return {
        "check_type": "RANGE",
        "table": table_name,
        "column": col,
        "status": "PASS" if invalid_count == 0 else "FAIL",
        "invalid_count": invalid_count,
        "severity": severity,
        "detail": f"expected between [{min_val}, {max_val}]",
    }


def check_allowed_set(
    df: pd.DataFrame,
    table_name: str,
    col: str,
    allowed_values: set[Any],
    severity: str,
) -> dict[str, Any]:
    invalid_mask = ~df[col].isin(allowed_values)
    invalid_count = int(invalid_mask.sum())
    return {
        "check_type": "ALLOWED_SET",
        "table": table_name,
        "column": col,
        "status": "PASS" if invalid_count == 0 else "FAIL",
        "invalid_count": invalid_count,
        "severity": severity,
        "detail": f"allowed={sorted(allowed_values)}",
    }


def run_checks(tables: dict[str, pd.DataFrame], rules: dict[str, Any]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []

    for rule in rules.get("primary_keys", []):
        records.append(
            check_pk_unique(
                tables[rule["table"]],
                rule["table"],
                rule["column"],
                rule.get("severity", "major"),
            )
        )

    for rule in rules.get("foreign_keys", []):
        records.append(
            check_fk_coverage(
                tables[rule["child_table"]],
                rule["child_table"],
                rule["child_column"],
                tables[rule["parent_table"]],
                rule["parent_table"],
                rule["parent_column"],
                rule.get("severity", "major"),
            )
        )

    for rule in rules.get("range_rules", []):
        table_name = rule["table"]
        col = rule["column"]
        min_val = rule["min"]
        max_val = rule.get("max", float(tables[table_name][col].max()))
        records.append(
            check_range(
                tables[table_name],
                table_name,
                col,
                min_val,
                max_val,
                rule.get("severity", "major"),
            )
        )

    for rule in rules.get("allowed_set_rules", []):
        records.append(
            check_allowed_set(
                tables[rule["table"]],
                rule["table"],
                rule["column"],
                set(rule["allowed_values"]),
                rule.get("severity", "major"),
            )
        )

    return pd.DataFrame(records)


def apply_imputations(
    tables: dict[str, pd.DataFrame],
    imputations: list[dict[str, Any]],
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    clean_tables = {name: df.copy() for name, df in tables.items()}
    logs: list[dict[str, Any]] = []

    for imp in imputations:
        table = imp["table"]
        col = imp["column"]
        fill_value = imp["fill_value"]
        reason = imp.get("reason", "")
        cast_dtype = imp.get("dtype")

        before_missing = int(clean_tables[table][col].isna().sum())
        clean_tables[table][col] = clean_tables[table][col].fillna(fill_value)
        if cast_dtype:
            clean_tables[table][col] = clean_tables[table][col].astype(cast_dtype)
        after_missing = int(clean_tables[table][col].isna().sum())

        logs.append(
            {
                "table": table,
                "column": col,
                "fill_value": str(fill_value),
                "missing_before": before_missing,
                "missing_after": after_missing,
                "filled_count": before_missing - after_missing,
                "reason": reason,
            }
        )

    return clean_tables, pd.DataFrame(logs)


def compute_summary(checks_df: pd.DataFrame) -> pd.Series:
    if checks_df.empty:
        return pd.Series(
            {
                "total_checks": 0,
                "pass_checks": 0,
                "fail_checks": 0,
                "pass_rate_pct": 0.0,
                "critical_failures": 0,
                "major_failures": 0,
            }
        )

    return pd.Series(
        {
            "total_checks": int(len(checks_df)),
            "pass_checks": int((checks_df["status"] == "PASS").sum()),
            "fail_checks": int((checks_df["status"] == "FAIL").sum()),
            "pass_rate_pct": round(float((checks_df["status"] == "PASS").mean() * 100), 2),
            "critical_failures": int(
                ((checks_df["status"] == "FAIL") & (checks_df["severity"] == "critical")).sum()
            ),
            "major_failures": int(
                ((checks_df["status"] == "FAIL") & (checks_df["severity"] == "major")).sum()
            ),
        }
    )


def create_relational_samples(
    tables: dict[str, pd.DataFrame],
    output_dir: Path,
    sample_size: int = 1000,
    random_state: int = 42,
) -> dict[str, pd.DataFrame]:
    """
    Create relational samples maintaining referential integrity.

    Steps:
    1. Sample order_ids from Orders table (PRIMARY)
    2. Filter Order_Products tables by sampled order_ids (CHILD)
    3. Filter Products by product_ids in Order_Products (CHILD)
    4. Filter Aisles and Departments by referenced IDs (DIMENSION)

    Args:
        tables: Dictionary of DataFrames
        output_dir: Directory to write sample files
        sample_size: Number of orders to sample
        random_state: For reproducibility

    Returns:
        Dictionary of sampled DataFrames
    """
    # Step 1: Sample order_ids from Orders (PRIMARY)
    sampled_orders = tables["orders"].sample(n=sample_size, random_state=random_state)
    sampled_order_ids = set(sampled_orders["order_id"].unique())

    # Step 2: Filter Order_Products by sampled order_ids (CHILD)
    sampled_order_products_prior = (
        tables["order_products_prior"][
            tables["order_products_prior"]["order_id"].isin(sampled_order_ids)
        ]
        .reset_index(drop=True)
    )
    sampled_order_products_train = (
        tables["order_products_train"][
            tables["order_products_train"]["order_id"].isin(sampled_order_ids)
        ]
        .reset_index(drop=True)
    )

    # Step 3: Get product_ids from sampled order_products
    sampled_product_ids = set()
    sampled_product_ids.update(sampled_order_products_prior["product_id"].unique())
    sampled_product_ids.update(sampled_order_products_train["product_id"].unique())

    # Step 4: Filter Products by sampled product_ids (CHILD)
    sampled_products = (
        tables["products"][tables["products"]["product_id"].isin(sampled_product_ids)]
        .reset_index(drop=True)
    )

    # Step 5: Get dimension IDs from sampled products
    sampled_aisle_ids = set(sampled_products["aisle_id"].dropna().unique())
    sampled_dept_ids = set(sampled_products["department_id"].dropna().unique())

    # Step 6: Filter Aisles and Departments (DIMENSIONS)
    sampled_aisles = (
        tables["aisles"][tables["aisles"]["aisle_id"].isin(sampled_aisle_ids)]
        .reset_index(drop=True)
    )
    sampled_departments = (
        tables["departments"][tables["departments"]["department_id"].isin(sampled_dept_ids)]
        .reset_index(drop=True)
    )

    # Step 7: Write all samples
    samples = {
        "orders": sampled_orders,
        "order_products_prior": sampled_order_products_prior,
        "order_products_train": sampled_order_products_train,
        "products": sampled_products,
        "aisles": sampled_aisles,
        "departments": sampled_departments,
    }

    for name, df in samples.items():
        # Write as _sample.csv
        file_path = output_dir / f"{name}_sample.csv"
        df.to_csv(file_path, index=False)
        
        # Also write as _clean_sample.csv for backward compatibility with notebooks
        file_path_clean_sample = output_dir / f"{name}_clean_sample.csv"
        df.to_csv(file_path_clean_sample, index=False)

    return samples


def run_data_quality_pipeline(
    raw_dir: Path,
    output_dir: Path,
    config_path: Path,
    export_reports: bool = True,
) -> dict[str, Any]:
    raw_dir = raw_dir.resolve()
    output_dir = output_dir.resolve()
    config_path = config_path.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rules = load_rules(config_path)
    tables = load_tables(raw_dir)

    profile_df = profile_tables(tables)
    missing_df = column_missing(tables)
    checks_df = run_checks(tables, rules)

    issue_register = (
        checks_df.query("status == 'FAIL'")
        .sort_values(["severity", "invalid_count"], ascending=[True, False])
        .reset_index(drop=True)
    )

    clean_tables, imputation_df = apply_imputations(tables, rules.get("imputations", []))

    missing_before = profile_df[["table", "missing_cells"]].rename(
        columns={"missing_cells": "missing_before"}
    )
    missing_after = profile_tables(clean_tables)[["table", "missing_cells"]].rename(
        columns={"missing_cells": "missing_after"}
    )
    missing_comparison = missing_before.merge(
        missing_after,
        on="table",
        how="left",
        validate="one_to_one",
    )
    missing_comparison["filled_cells"] = (
        missing_comparison["missing_before"] - missing_comparison["missing_after"]
    )

    summary_kpi = compute_summary(checks_df)

    if export_reports:
        profile_df.to_csv(output_dir / "table_profile.csv", index=False)
        missing_df.to_csv(output_dir / "column_missing.csv", index=False)
        checks_df.to_csv(output_dir / "check_results.csv", index=False)
        issue_register.to_csv(output_dir / "issue_register.csv", index=False)
        imputation_df.to_csv(output_dir / "imputation_log.csv", index=False)
        missing_comparison.to_csv(output_dir / "missing_comparison_before_after.csv", index=False)
        summary_kpi.to_frame(name="value").to_csv(output_dir / "summary_kpi.csv")

    for table_name, df in clean_tables.items():
        df.to_csv(output_dir / f"{table_name}_clean.csv", index=False)

    project_root = next(
        (
            candidate
            for candidate in [output_dir, *output_dir.parents]
            if (candidate / "src").exists() and (candidate / "data").exists()
        ),
        None,
    )
    if project_root is None:
        raise FileNotFoundError(
            f"Could not resolve project root from output directory: {output_dir}"
        )

    # Save full feature table (ignored by git by default)
    cumulative_feature_full = build_customer_cumulative_reorder_feature(
        clean_tables["orders"],
        clean_tables["order_products_prior"],
    )
    cumulative_feature_full.to_csv(
        output_dir / "customer_cumulative_reorder_clean.csv",
        index=False,
    )

    # Create relational samples from clean tables
    sample_tables = create_relational_samples(clean_tables, output_dir, sample_size=1000)

    # Save sample feature table (tracked by git)
    cumulative_feature_sample = build_customer_cumulative_reorder_feature(
        sample_tables["orders"],
        sample_tables["order_products_prior"],
    )
    cumulative_feature_sample.to_csv(
        output_dir / "customer_cumulative_reorder_sample.csv",
        index=False,
    )
    cumulative_feature_sample.to_csv(
        output_dir / "customer_cumulative_reorder_clean_sample.csv",
        index=False,
    )

    full_feature_result = run_feature_engineering_pipeline(
        use_sample=False,
        project_root=project_root,
    )
    sample_feature_result = run_feature_engineering_pipeline(
        use_sample=True,
        project_root=project_root,
    )

    return {
        "output_dir": str(output_dir),
        "export_reports": bool(export_reports),
        "total_checks": int(summary_kpi["total_checks"]),
        "pass_checks": int(summary_kpi["pass_checks"]),
        "fail_checks": int(summary_kpi["fail_checks"]),
        "pass_rate_pct": float(summary_kpi["pass_rate_pct"]),
        "critical_failures": int(summary_kpi["critical_failures"]),
        "major_failures": int(summary_kpi["major_failures"]),
        "issues_count": int(len(issue_register)),
        "full_feature_dir": full_feature_result["feature_dir"],
        "sample_feature_dir": sample_feature_result["feature_dir"],
    }
