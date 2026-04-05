from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from instacart_quality.features import build_orders_with_dates


class BuildOrdersWithDatesTests(unittest.TestCase):
    def test_build_orders_with_dates_preserves_chronology(self) -> None:
        orders = pd.DataFrame(
            {
                "order_id": [1, 2, 3],
                "user_id": [42, 42, 42],
                "order_number": [1, 2, 3],
                "days_since_prior_order": [None, 10, 5],
            }
        )

        result = build_orders_with_dates(orders, snapshot_date="2015-07-01")
        result = result.sort_values("order_number").reset_index(drop=True)

        self.assertEqual(
            list(result["order_date"].dt.strftime("%Y-%m-%d")),
            ["2015-06-16", "2015-06-26", "2015-07-01"],
        )
        self.assertTrue(result["order_date"].is_monotonic_increasing)
        self.assertEqual(
            result.loc[result["order_number"].idxmax(), "order_date"],
            pd.Timestamp("2015-07-01"),
        )


if __name__ == "__main__":
    unittest.main()
