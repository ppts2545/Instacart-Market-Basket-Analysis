#!/usr/bin/env python
"""
Create sample versions of clean quality datasets for faster notebook development.
Maintains referential integrity by sampling users and their related orders.
"""

import sys
from pathlib import Path
import pandas as pd

# Resolve project root
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from instacart_quality import resolve_project_root, load_quality_table

PROJECT_ROOT = resolve_project_root()
QUALITY_DIR = PROJECT_ROOT / "data" / "processed" / "quality"

# Sample size: consistent 5000 users for manageable EDA notebooks
SAMPLE_USERS = 5000

def create_quality_samples():
    """Create sample versions of all quality tables by sampling users."""
    
    print("=" * 70)
    print("CREATING QUALITY SAMPLE DATASETS")
    print("=" * 70)
    
    # Load full tables
    print("\n📦 Loading full quality tables...")
    orders_full = load_quality_table("orders", use_sample=False, project_root=PROJECT_ROOT)
    order_products_prior_full = load_quality_table("order_products_prior", use_sample=False, project_root=PROJECT_ROOT)
    order_products_train_full = load_quality_table("order_products_train", use_sample=False, project_root=PROJECT_ROOT)
    products_full = load_quality_table("products", use_sample=False, project_root=PROJECT_ROOT)
    aisles_full = load_quality_table("aisles", use_sample=False, project_root=PROJECT_ROOT)
    departments_full = load_quality_table("departments", use_sample=False, project_root=PROJECT_ROOT)
    customer_cumulative_reorder_full = load_quality_table("customer_cumulative_reorder", use_sample=False, project_root=PROJECT_ROOT)
    
    print(f"✓ Orders: {len(orders_full):,} rows")
    print(f"✓ Order Products Prior: {len(order_products_prior_full):,} rows")
    print(f"✓ Order Products Train: {len(order_products_train_full):,} rows")
    print(f"✓ Products: {len(products_full):,} rows")
    print(f"✓ Aisles: {len(aisles_full):,} rows")
    print(f"✓ Departments: {len(departments_full):,} rows")
    print(f"✓ Customer Cumulative Reorder: {len(customer_cumulative_reorder_full):,} rows")
    
    # Sample users consistently
    print(f"\n🎯 Sampling {SAMPLE_USERS:,} users...")
    all_users = orders_full["user_id"].unique()
    sample_users = sorted(pd.Series(all_users).sample(n=min(SAMPLE_USERS, len(all_users)), random_state=42).tolist())
    print(f"✓ Sampled {len(sample_users):,} users")
    
    # Sample orders by user
    orders_sample = orders_full[orders_full["user_id"].isin(sample_users)].copy()
    sample_order_ids = set(orders_sample["order_id"].unique())
    print(f"✓ Sampled {len(orders_sample):,} orders")
    
    # Sample order_products by sampled orders
    order_products_prior_sample = order_products_prior_full[
        order_products_prior_full["order_id"].isin(sample_order_ids)
    ].copy()
    print(f"✓ Sampled {len(order_products_prior_sample):,} order lines (prior)")
    
    order_products_train_sample = order_products_train_full[
        order_products_train_full["order_id"].isin(sample_order_ids)
    ].copy()
    print(f"✓ Sampled {len(order_products_train_sample):,} order lines (train)")
    
    # Sample products referenced in sampled orders
    products_in_sample = set(
        pd.concat([
            order_products_prior_sample["product_id"],
            order_products_train_sample["product_id"]
        ]).unique()
    )
    products_sample = products_full[products_full["product_id"].isin(products_in_sample)].copy()
    print(f"✓ Sampled {len(products_sample):,} products")
    
    # Keep dimension tables complete (small size, helps integrity)
    aisles_sample = aisles_full.copy()
    departments_sample = departments_full.copy()
    customer_cumulative_reorder_sample = customer_cumulative_reorder_full[
        customer_cumulative_reorder_full["user_id"].isin(sample_users)
    ].copy()
    print(f"✓ Kept all aisles ({len(aisles_sample):,})")
    print(f"✓ Kept all departments ({len(departments_sample):,})")
    print(f"✓ Sampled {len(customer_cumulative_reorder_sample):,} customer cumulative reorder records")
    
    # Save samples
    print(f"\n💾 Writing sample files to {QUALITY_DIR}...")
    
    files_to_save = {
        "orders_clean_sample.csv": orders_sample,
        "order_products_prior_clean_sample.csv": order_products_prior_sample,
        "order_products_train_clean_sample.csv": order_products_train_sample,
        "products_clean_sample.csv": products_sample,
        "aisles_clean_sample.csv": aisles_sample,
        "departments_clean_sample.csv": departments_sample,
        "customer_cumulative_reorder_clean_sample.csv": customer_cumulative_reorder_sample,
    }
    
    for filename, df in files_to_save.items():
        file_path = QUALITY_DIR / filename
        df.to_csv(file_path, index=False)
        print(f"✓ {filename}: {len(df):,} rows")
    
    print(f"\n{'=' * 70}")
    print("✅ SAMPLE QUALITY DATASETS CREATED SUCCESSFULLY")
    print(f"{'=' * 70}")
    
    # Print summary
    print("\n📊 Sample File Summary:")
    print(f"  Total users: {len(sample_users):,}")
    print(f"  Total orders: {len(orders_sample):,}")
    print(f"  Total order lines: {len(order_products_prior_sample) + len(order_products_train_sample):,}")
    print(f"\nAll EDA notebooks can now use sample=True for faster iteration!")

if __name__ == "__main__":
    create_quality_samples()
