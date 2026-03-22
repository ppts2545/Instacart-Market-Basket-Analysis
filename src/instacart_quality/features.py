from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .data_access import load_quality_table, resolve_project_root


def get_feature_dir(project_root: Path | None = None, create: bool = False) -> Path:
    root = project_root.resolve() if project_root else resolve_project_root()
    feature_dir = root / "data" / "processed" / "features"
    if create:
        feature_dir.mkdir(parents=True, exist_ok=True)
    return feature_dir


def build_orders_with_dates(
    orders_df: pd.DataFrame,
    snapshot_date: pd.Timestamp | str = "2015-07-01",
) -> pd.DataFrame:
    """Build order-level dates from days_since_prior_order per user."""
    snapshot = pd.Timestamp(snapshot_date)
    orders_sorted = orders_df.sort_values(["user_id", "order_number"]).reset_index(drop=True)
    orders_sorted["days_since_prior_order"] = orders_sorted["days_since_prior_order"].fillna(0)
    orders_sorted["cumulative_days"] = (
        orders_sorted.groupby("user_id")["days_since_prior_order"].cumsum()
    )
    orders_sorted["order_date"] = snapshot - pd.to_timedelta(
        orders_sorted["cumulative_days"], unit="D"
    )
    return orders_sorted


def build_customer_product_reorder_count(
    orders_df: pd.DataFrame,
    order_products_prior_df: pd.DataFrame,
    products_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build customer-product reorder count feature table."""
    base = orders_df[["order_id", "user_id"]].merge(
        order_products_prior_df[["order_id", "product_id", "reordered"]],
        on="order_id",
        how="inner",
    )

    feature = (
        base.groupby(["user_id", "product_id"], as_index=False)["reordered"]
        .sum()
        .rename(columns={"reordered": "reorder_count"})
    )

    if products_df is not None and "product_name" in products_df.columns:
        feature = feature.merge(
            products_df[["product_id", "product_name"]],
            on="product_id",
            how="left",
        )
    return feature


def run_feature_engineering_pipeline(
    use_sample: bool = True,
    project_root: Path | None = None,
    snapshot_date: str = "2015-07-01",
) -> dict[str, Any]:
    """Generate engineered datasets under data/processed/features."""
    root = project_root.resolve() if project_root else resolve_project_root()
    mode = "sample" if use_sample else "full"
    suffix = "_sample" if use_sample else ""

    orders = load_quality_table("orders", use_sample=use_sample, project_root=root)
    order_products_prior = load_quality_table(
        "order_products_prior", use_sample=use_sample, project_root=root
    )
    products = load_quality_table("products", use_sample=use_sample, project_root=root)

    feature_dir = get_feature_dir(project_root=root, create=True)

    orders_with_dates = build_orders_with_dates(orders, snapshot_date=snapshot_date)
    customer_product_reorder = build_customer_product_reorder_count(
        orders_df=orders_with_dates,
        order_products_prior_df=order_products_prior,
        products_df=products,
    )

    orders_path = feature_dir / f"orders_with_dates{suffix}.csv"
    customer_product_path = feature_dir / f"customer_product_reorder_count{suffix}.csv"

    orders_with_dates.to_csv(orders_path, index=False)
    customer_product_reorder.to_csv(customer_product_path, index=False)

    return {
        "mode": mode,
        "feature_dir": str(feature_dir),
        "orders_with_dates_path": str(orders_path),
        "orders_rows": int(len(orders_with_dates)),
        "customer_product_reorder_path": str(customer_product_path),
        "customer_product_reorder_rows": int(len(customer_product_reorder)),
    }
