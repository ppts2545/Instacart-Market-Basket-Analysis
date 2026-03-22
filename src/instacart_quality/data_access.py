from __future__ import annotations

from pathlib import Path

import pandas as pd


QUALITY_TABLE_FILES = {
    "orders": {"sample": "orders_clean_sample.csv", "full": "orders_clean.csv"},
    "order_products_prior": {
        "sample": "order_products_prior_clean_sample.csv",
        "full": "order_products_prior_clean.csv",
    },
    "order_products_train": {
        "sample": "order_products_train_clean_sample.csv",
        "full": "order_products_train_clean.csv",
    },
    "products": {"sample": "products_clean_sample.csv", "full": "products_clean.csv"},
    "aisles": {"sample": "aisles_clean_sample.csv", "full": "aisles_clean.csv"},
    "departments": {
        "sample": "departments_clean_sample.csv",
        "full": "departments_clean.csv",
    },
    "customer_cumulative_reorder": {
        "sample": "customer_cumulative_reorder_clean_sample.csv",
        "full": "customer_cumulative_reorder_clean.csv",
    },
}

FEATURE_TABLE_FILES = {
    "orders_with_dates": "orders_with_dates",
    "customer_product_reorder_count": "customer_product_reorder_count",
}


def resolve_project_root(start_path: Path | None = None) -> Path:
    """Resolve project root by walking up from cwd (or a given path)."""
    candidate = (start_path or Path.cwd()).resolve()
    if candidate.is_file():
        candidate = candidate.parent

    markers = ("README.md", "src", "data")
    for path in [candidate, *candidate.parents]:
        if all((path / marker).exists() for marker in markers):
            return path

    raise FileNotFoundError(
        "Could not resolve project root. Expected folder containing README.md, src, and data."
    )


def get_quality_dir(project_root: Path | None = None) -> Path:
    root = project_root.resolve() if project_root else resolve_project_root()
    quality_dir = root / "data" / "processed" / "quality"
    if not quality_dir.exists():
        raise FileNotFoundError(f"Quality directory not found: {quality_dir}")
    return quality_dir


def get_feature_dir(project_root: Path | None = None) -> Path:
    root = project_root.resolve() if project_root else resolve_project_root()
    feature_dir = root / "data" / "processed" / "features"
    feature_dir.mkdir(parents=True, exist_ok=True)
    return feature_dir


def ensure_feature_table(
    feature_name: str,
    use_sample: bool = True,
    project_root: Path | None = None,
) -> Path:
    """Return a feature-table path, generating it if it does not exist yet."""
    if feature_name not in FEATURE_TABLE_FILES:
        allowed = ", ".join(sorted(FEATURE_TABLE_FILES.keys()))
        raise KeyError(f"Unknown feature_name '{feature_name}'. Allowed: {allowed}")

    root = project_root.resolve() if project_root else resolve_project_root()
    feature_dir = get_feature_dir(root)
    suffix = "_sample" if use_sample else ""
    feature_path = feature_dir / f"{FEATURE_TABLE_FILES[feature_name]}{suffix}.csv"

    if feature_path.exists():
        return feature_path

    from .features import run_feature_engineering_pipeline

    run_feature_engineering_pipeline(use_sample=use_sample, project_root=root)

    if feature_path.exists():
        return feature_path

    raise FileNotFoundError(
        f"Feature file could not be created: {feature_path}\n"
        "Run the feature engineering pipeline and confirm clean quality tables exist first."
    )


def load_quality_table(
    table_name: str,
    use_sample: bool = True,
    project_root: Path | None = None,
) -> pd.DataFrame:
    """Load one standardized table from data/processed/quality.
    
    Falls back to full dataset if sample file is not found.
    """
    if table_name not in QUALITY_TABLE_FILES:
        allowed = ", ".join(sorted(QUALITY_TABLE_FILES.keys()))
        raise KeyError(f"Unknown table_name '{table_name}'. Allowed: {allowed}")

    quality_dir = get_quality_dir(project_root)
    
    # Try preferred mode first
    mode = "sample" if use_sample else "full"
    file_path = quality_dir / QUALITY_TABLE_FILES[table_name][mode]
    
    # Fallback to full if sample doesn't exist
    if not file_path.exists() and use_sample:
        file_path = quality_dir / QUALITY_TABLE_FILES[table_name]["full"]
    
    if not file_path.exists():
        raise FileNotFoundError(f"Expected file not found: {file_path}")

    return pd.read_csv(file_path)


def load_eda_base(use_sample: bool = True, project_root: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load the core cleaned tables most EDA notebooks need."""
    return {
        "orders": load_quality_table("orders", use_sample=use_sample, project_root=project_root),
        "order_products_prior": load_quality_table(
            "order_products_prior", use_sample=use_sample, project_root=project_root
        ),
        "order_products_train": load_quality_table(
            "order_products_train", use_sample=use_sample, project_root=project_root
        ),
        "products": load_quality_table("products", use_sample=use_sample, project_root=project_root),
        "aisles": load_quality_table("aisles", use_sample=use_sample, project_root=project_root),
        "departments": load_quality_table(
            "departments", use_sample=use_sample, project_root=project_root
        ),
    }


def load_product_dimension(
    use_sample: bool = True,
    project_root: Path | None = None,
) -> pd.DataFrame:
    """Load products enriched with aisle and department information.
    
    Merges products table with aisles and departments for category analysis.
    
    Parameters
    ----------
    use_sample : bool, default True
        Load sample or full dataset.
    project_root : Path | None, default None
        Project root path. If None, will be resolved automatically.
    
    Returns
    -------
    pd.DataFrame
        Products dimension with columns: product_id, product_name, aisle_id, aisle,
        department_id, department.
    """
    root = project_root.resolve() if project_root else resolve_project_root()
    
    products = load_quality_table("products", use_sample=use_sample, project_root=root)
    aisles = load_quality_table("aisles", use_sample=use_sample, project_root=root)
    departments = load_quality_table("departments", use_sample=use_sample, project_root=root)
    
    product_dim = products.merge(aisles, on="aisle_id", how="left").merge(
        departments, on="department_id", how="left"
    )
    
    return product_dim


def load_order_products_with_product_dim(
    use_sample: bool = True,
    project_root: Path | None = None,
) -> pd.DataFrame:
    """Load order_products_prior enriched with product, aisle, and department information.
    
    Merges order_products_prior with the full product dimension for category analysis.
    
    Parameters
    ----------
    use_sample : bool, default True
        Load sample or full dataset.
    project_root : Path | None, default None
        Project root path. If None, will be resolved automatically.
    
    Returns
    -------
    pd.DataFrame
        Order-product data with all product dimension columns.
    """
    root = project_root.resolve() if project_root else resolve_project_root()
    
    order_products = load_quality_table(
        "order_products_prior", use_sample=use_sample, project_root=root
    )
    product_dim = load_product_dimension(use_sample=use_sample, project_root=root)
    
    df = order_products.merge(product_dim, on="product_id", how="left")
    
    # Validate required columns
    required_cols = ["product_name", "aisle", "department"]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns after merge: {missing_cols}")
    
    return df


def load_customer_behavior_data(
    use_sample: bool = True,
    project_root: Path | None = None,
) -> pd.DataFrame:
    """Load and enrich customer behavior data with dates and product information.
    
    Combines order_products_prior, orders (with calculated dates), and products
    into a single enriched dataframe for customer behavior analysis.
    
    Parameters
    ----------
    use_sample : bool, default True
        Load sample (5000 users) or full dataset.
    project_root : Path | None, default None
        Project root path. If None, will be resolved automatically.
    
    Returns
    -------
    pd.DataFrame
        Enriched dataframe with columns:
        - order dates (calculated from orders_with_dates.csv)
        - product names and metadata
        - computed fields: total_price, cumulative_reorder_per_customer
    """
    root = project_root.resolve() if project_root else resolve_project_root()
    
    # Load base tables
    order_products = load_quality_table(
        "order_products_prior", use_sample=use_sample, project_root=root
    )
    products = load_quality_table("products", use_sample=use_sample, project_root=root)
    
    # Load canonical feature artifact and auto-generate it if missing.
    orders_path = ensure_feature_table(
        "orders_with_dates",
        use_sample=use_sample,
        project_root=root,
    )
    
    orders = pd.read_csv(orders_path)
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    
    # Merge order_products with orders (to get dates)
    df = order_products.merge(orders, on="order_id", how="left")
    
    # Merge with products (to get product name)
    df = df.merge(products[["product_id", "product_name"]], on="product_id", how="left")
    
    # Add computed columns
    df["total_price"] = 1  # Proxy for monetary value (item count)
    df = df.sort_values(["user_id", "order_number", "add_to_cart_order"]).reset_index(drop=True)
    df["cumulative_reorder_per_customer"] = df.groupby("user_id")["reordered"].cumsum()
    
    return df