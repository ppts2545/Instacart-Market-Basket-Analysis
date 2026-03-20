# Relational Sampling in Instacart Data

## ❌ Problem: Independent Sampling (WRONG)

Previously, sample files were created by sampling each table **independently**, which broke referential integrity:

```python
# ❌ WRONG - Independent sampling breaks relationships
orders_sample = orders.sample(n=1000)  # 1000 random orders
products_sample = products.sample(n=5000)  # 5000 random products (unrelated!)
order_products_sample = order_products.sample(n=10000)  # 10000 random rows

# Result: Products in order_products might not exist in products_sample
# Foreign key constraints violated ❌
```

**Consequences:**
- Foreign key relationships are broken
- Analysis results can't be validated on sample data
- Tests using samples will give false negatives
- Merges/joins produce unexpected NAs or orphaned rows

---

## ✓ Solution: Relational Sampling (CORRECT)

Samples are now created following the **referential hierarchy**, starting from the primary table:

### Sampling Order:

1. **PRIMARY TABLE: Orders**
   ```
   Sample N order_ids from orders table
   Example: 1,000 out of 3.4M orders
   ```

2. **CHILD 1: Order_Products (Prior)** 
   ```
   Filter to rows where order_id ∈ {1000 sampled order_ids}
   Keep all products for those orders
   ```

3. **CHILD 2: Order_Products (Train)**
   ```
   Filter to rows where order_id ∈ {1000 sampled order_ids}
   Keep all products for those orders
   ```

4. **GRANDCHILD: Products**
   ```
   Collect all product_ids from filtered order_products
   Filter products table to rows with those product_ids
   Result: Only products that appear in sampled orders
   ```

5. **DIMENSION TABLES: Aisles & Departments**
   ```
   Collect aisle_ids and department_ids from filtered products
   Filter dimension tables accordingly
   Result: Only aisles/departments referenced by sampled products
   ```

### Diagram:

```
Orders (1000)
    ↓
    ├→ Order_Products_Prior (9,356)  [1-to-Many]
    ├→ Order_Products_Train (560)    [1-to-Many]
         ↓
         └→ Products (4,553)
              ↓
              ├→ Aisles (134)      [1-to-Many when reversed]
              └→ Departments (21)  [1-to-Many when reversed]
```

---

## Current Sample Sizes (1000 orders)

| Table | Rows | Description |
|-------|------|-------------|
| **orders** | **1,000** | Primary sample |
| **order_products_prior** | 9,356 | All prior purchases for sampled orders |
| **order_products_train** | 560 | All train purchases for sampled orders |
| **products** | 4,553 | All products in sampled orders |
| **aisles** | 134 | All aisles referenced by sampled products |
| **departments** | 21 | All departments referenced by sampled products |

---

## ✓ Validation Results

All referential integrity constraints **PASS**:

```
✓ order_products_prior.order_id ⊆ orders.order_id         (100.00%)
✓ order_products_train.order_id ⊆ orders.order_id         (100.00%)
✓ order_products_prior.product_id ⊆ products.product_id   (100.00%)
✓ order_products_train.product_id ⊆ products.product_id   (100.00%)
✓ products.aisle_id ⊆ aisles.aisle_id                     (100.00%)
✓ products.department_id ⊆ departments.department_id      (100.00%)
```

---

## How to Use Sample Data

### Option 1: Auto-generated Samples (Recommended)

The data quality pipeline now **automatically** creates relational samples:

```bash
python scripts/run_data_quality.py
```

This produces:
- `data/processed/quality/*_clean.csv` (full cleaned data)
- `data/processed/quality/*_sample.csv` (relational samples, ~1000 orders)

### Option 2: Manual Sampling with Custom Size

Create samples with a different size:

```bash
source .venv/bin/activate
python scripts/create_relational_samples.py --sample-size 2000
```

### Option 3: In Notebook Code

```python
import pandas as pd
from pathlib import Path

DATA_DIR = Path('data/processed/quality')

# Load sample data (preserves all relationships)
orders_sample = pd.read_csv(DATA_DIR / 'orders_sample.csv')
op_prior_sample = pd.read_csv(DATA_DIR / 'order_products_prior_sample.csv')

# Safe to join - all order_ids in prior exist in orders
merged = op_prior_sample.merge(orders_sample, on='order_id', how='left')
assert merged['order_id'].notna().all()  # ✓ No NAs after join
```

---

## Design Principles

1. **Referential Integrity First**
   - Every foreign key reference points to an existing row
   - No orphaned or dangling records

2. **Stratified Preservation**
   - All products in an order are kept together
   - Sample represents actual purchasing patterns

3. **Hierarchical Filtering**
   - Start from root (orders), cascade down to dimensions
   - Never sample child tables independently

4. **Reproducibility**
   - Fixed `random_state=42` for consistent results
   - Same 1000 orders selected every pipeline run

---

## Files Modified

- **`scripts/create_relational_samples.py`** - Standalone sampling script
- **`src/instacart_quality/pipeline.py`** - Integrated relational sampling function
- **`scripts/run_data_quality.py`** - Now calls sampling after data cleaning

---

## Key Takeaway

**Never sample related tables independently.** Always follow the referential hierarchy, starting from the primary table and filtering child/dimension tables based on what appears in the parent sample.

This ensures your sample is a true, representative subset of the full data with all relationships intact.
