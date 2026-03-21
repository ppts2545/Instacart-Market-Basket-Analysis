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


def load_quality_table(
    table_name: str,
    use_sample: bool = True,
    project_root: Path | None = None,
) -> pd.DataFrame:
    """Load one standardized table from data/processed/quality."""
    if table_name not in QUALITY_TABLE_FILES:
        allowed = ", ".join(sorted(QUALITY_TABLE_FILES.keys()))
        raise KeyError(f"Unknown table_name '{table_name}'. Allowed: {allowed}")

    mode = "sample" if use_sample else "full"
    quality_dir = get_quality_dir(project_root)
    file_path = quality_dir / QUALITY_TABLE_FILES[table_name][mode]
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