"""
Create relational samples maintaining referential integrity.

This script samples from the Orders table first (primary table),
then filters all related tables to include only rows that reference
the sampled orders. This preserves the 1-to-many relationships.

Usage:
    python scripts/create_relational_samples.py --sample-size 1000
"""

import argparse
from pathlib import Path

import pandas as pd


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


def create_relational_samples(
    raw_dir: Path,
    output_dir: Path,
    sample_size: int = 1000,
    random_state: int = 42,
) -> dict[str, pd.DataFrame]:
    """
    Create relational samples from Instacart data.

    Steps:
    1. Sample order_ids from Orders table (PRIMARY)
    2. Filter Order_Products tables by sampled order_ids (CHILD)
    3. Filter Products by product_ids found in sampled Order_Products (CHILD)
    4. Filter Aisles and Departments by what's referenced in Products (CHILD)

    Args:
        raw_dir: Path to raw data directory
        output_dir: Path to write sample files
        sample_size: Number of orders to sample
        random_state: For reproducibility

    Returns:
        Dictionary of sampled DataFrames
    """
    raw_dir = raw_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Creating relational samples (n={sample_size})...")
    print(f"Raw data: {raw_dir}")
    print(f"Output: {output_dir}\n")

    # Step 1: Load primary table (Orders)
    print("Step 1: Loading Orders table (PRIMARY)...")
    orders = pd.read_csv(raw_dir / "orders.csv")
    print(f"  Orders: {len(orders):,} rows")

    # Step 2: Sample from Orders
    print(f"\nStep 2: Sampling {sample_size:,} order_ids from {len(orders):,} total orders...")
    sampled_orders = orders.sample(n=sample_size, random_state=random_state)
    sampled_order_ids = set(sampled_orders["order_id"].unique())
    print(f"  Sampled order_ids: {len(sampled_order_ids):,}")

    # Step 3: Filter Order_Products__Prior by sampled order_ids
    print("\nStep 3: Filtering Order_Products__Prior (CHILD)...")
    order_products_prior = pd.read_csv(raw_dir / "order_products__prior.csv")
    sampled_order_products_prior = order_products_prior[
        order_products_prior["order_id"].isin(sampled_order_ids)
    ].reset_index(drop=True)
    print(
        f"  Original: {len(order_products_prior):,} rows "
        f"→ Sampled: {len(sampled_order_products_prior):,} rows"
    )

    # Step 4: Filter Order_Products__Train by sampled order_ids
    print("\nStep 4: Filtering Order_Products__Train (CHILD)...")
    order_products_train = pd.read_csv(raw_dir / "order_products__train.csv")
    sampled_order_products_train = order_products_train[
        order_products_train["order_id"].isin(sampled_order_ids)
    ].reset_index(drop=True)
    print(
        f"  Original: {len(order_products_train):,} rows "
        f"→ Sampled: {len(sampled_order_products_train):,} rows"
    )

    # Step 5: Get unique product_ids from sampled order_products
    print("\nStep 5: Finding product_ids in sampled order_products...")
    sampled_product_ids = set()
    sampled_product_ids.update(sampled_order_products_prior["product_id"].unique())
    sampled_product_ids.update(sampled_order_products_train["product_id"].unique())
    print(f"  Unique product_ids: {len(sampled_product_ids):,}")

    # Step 6: Filter Products by sampled product_ids
    print("\nStep 6: Filtering Products (CHILD)...")
    products = pd.read_csv(raw_dir / "products.csv")
    sampled_products = products[products["product_id"].isin(sampled_product_ids)].reset_index(
        drop=True
    )
    print(
        f"  Original: {len(products):,} rows → Sampled: {len(sampled_products):,} rows"
    )

    # Step 7: Get unique aisle_ids and department_ids from sampled products
    print("\nStep 7: Finding dimension IDs in sampled products...")
    sampled_aisle_ids = set(sampled_products["aisle_id"].dropna().unique())
    sampled_dept_ids = set(sampled_products["department_id"].dropna().unique())
    print(f"  Unique aisle_ids: {len(sampled_aisle_ids):,}")
    print(f"  Unique department_ids: {len(sampled_dept_ids):,}")

    # Step 8: Filter Aisles and Departments
    print("\nStep 8: Filtering Aisles and Departments (DIMENSIONS)...")
    aisles = pd.read_csv(raw_dir / "aisles.csv")
    sampled_aisles = aisles[aisles["aisle_id"].isin(sampled_aisle_ids)].reset_index(
        drop=True
    )
    print(
        f"  Aisles: {len(aisles):,} rows → Sampled: {len(sampled_aisles):,} rows"
    )

    departments = pd.read_csv(raw_dir / "departments.csv")
    sampled_departments = departments[
        departments["department_id"].isin(sampled_dept_ids)
    ].reset_index(drop=True)
    print(
        f"  Departments: {len(departments):,} rows → Sampled: {len(sampled_departments):,} rows"
    )

    # Step 9: Write all samples
    print("\nStep 9: Writing sample files...")
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
        
        print(f"  ✓ {file_path.name} & {file_path_clean_sample.name} ({len(df):,} rows)")

    # Step 9.1: Build and write cumulative reorder feature sample
    cumulative_feature = build_customer_cumulative_reorder_feature(
        sampled_orders,
        sampled_order_products_prior,
    )
    feature_path = output_dir / "customer_cumulative_reorder_sample.csv"
    feature_clean_path = output_dir / "customer_cumulative_reorder_clean_sample.csv"
    cumulative_feature.to_csv(feature_path, index=False)
    cumulative_feature.to_csv(feature_clean_path, index=False)
    print(
        "  ✓ "
        f"{feature_path.name} & {feature_clean_path.name} "
        f"({len(cumulative_feature):,} rows)"
    )

    # Step 10: Validate relational integrity
    print("\nStep 10: Validating relational integrity...")
    validation_results = {
        "order_products_prior.order_id ⊆ orders.order_id": (
            sampled_order_products_prior["order_id"].isin(sampled_orders["order_id"]).all()
        ),
        "order_products_train.order_id ⊆ orders.order_id": (
            sampled_order_products_train["order_id"].isin(sampled_orders["order_id"]).all()
        ),
        "order_products_prior.product_id ⊆ products.product_id": (
            sampled_order_products_prior["product_id"].isin(sampled_products["product_id"]).all()
        ),
        "order_products_train.product_id ⊆ products.product_id": (
            sampled_order_products_train["product_id"].isin(sampled_products["product_id"]).all()
        ),
        "products.aisle_id ⊆ aisles.aisle_id": (
            sampled_products["aisle_id"].isin(sampled_aisles["aisle_id"]).all()
        ),
        "products.department_id ⊆ departments.department_id": (
            sampled_products["department_id"].isin(sampled_departments["department_id"]).all()
        ),
    }

    all_pass = all(validation_results.values())
    status = "✓ PASS" if all_pass else "✗ FAIL"
    print(f"\n  {status} Relational Integrity Check:")
    for check, result in validation_results.items():
        check_status = "✓" if result else "✗"
        print(f"    {check_status} {check}")

    return samples


def main():
    parser = argparse.ArgumentParser(
        description="Create relational samples from Instacart data with referential integrity."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory containing raw CSV files (default: data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/processed/quality"),
        help="Directory for sample files (default: data/processed/quality)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=1000,
        help="Number of orders to sample (default: 1000)",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )

    args = parser.parse_args()

    create_relational_samples(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        sample_size=args.sample_size,
        random_state=args.random_state,
    )

    print("\n✓ Relational sampling completed successfully!")


if __name__ == "__main__":
    main()
