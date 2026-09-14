from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from src.repository import AnalyticsRepository
from src.semantic_model import METRICS
from src.tools import analyze_revenue_drivers, diagnose_stores, forecast_metric, get_performance_summary, rank_performance

ROOT = Path(__file__).resolve().parents[1]


class AnalyticsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo = AnalyticsRepository(ROOT / "data" / "analytics.db")

    def test_latest_complete_week_is_monday_to_sunday(self) -> None:
        period = self.repo.resolve_period("latest_complete_week")
        self.assertEqual((period.start, period.end), ("2026-06-22", "2026-06-28"))

    def test_database_connection_is_read_only(self) -> None:
        with self.repo.connect() as connection:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("CREATE TABLE forbidden (id INTEGER)")

    def test_category_metrics_are_not_registered(self) -> None:
        self.assertFalse(any(metric.context == "category" for metric in METRICS.values()))

    def test_summary_uses_context_first_names(self) -> None:
        summary = get_performance_summary(self.repo, "ga")
        self.assertEqual(summary["metrics"][0]["metric"], "ga_revenue")
        self.assertTrue(all(metric["metric"].startswith("ga_") for metric in summary["metrics"]))

    def test_driver_contributions_reconcile_to_revenue_change(self) -> None:
        for context in ["digital", "store"]:
            result = analyze_revenue_drivers(self.repo, context)
            contribution = sum(item["revenue_contribution"] for item in result["factors"])
            change = result["revenue"]["change"]["absolute"]
            self.assertAlmostEqual(contribution, change, places=5)

    def test_invalid_dimension_is_blocked(self) -> None:
        with self.assertRaises(ValueError):
            rank_performance(self.repo, "digital_revenue", "channel")

    def test_store_diagnosis_returns_ranked_declines(self) -> None:
        result = diagnose_stores(self.repo, limit=5)
        changes = [store["revenue_change"]["absolute"] for store in result["stores"]]
        self.assertEqual(changes, sorted(changes))
        self.assertEqual(len(changes), 5)
        attention = result["attention_group"]
        self.assertAlmostEqual(
            attention["gross_store_revenue_decline"] + attention["offset_from_other_stores"],
            result["portfolio"]["change"]["absolute"],
        )

    def test_best_store_ranks_on_current_value_and_includes_profile(self) -> None:
        result = rank_performance(
            self.repo,
            "store_revenue",
            "store",
            direction="top",
            ranking_basis="value",
            limit=1,
        )
        all_stores = self.repo.metric_by_dimension(
            "store_revenue", "store", self.repo.resolve_period("latest_complete_week")
        )
        self.assertEqual(result["results"][0]["value"], max(row["value"] for row in all_stores))
        profile_labels = {metric["label"] for metric in result["results"][0]["profile"]}
        self.assertEqual(
            profile_labels,
            {"Store Revenue", "Store Traffic", "Store Orders", "Store Units", "Store Conversion", "Store AOV", "Store UPT"},
        )

    def test_forecast_is_positive_and_validated(self) -> None:
        result = forecast_metric(self.repo, "digital_revenue")
        self.assertGreater(result["forecast_total"], 0)
        self.assertEqual(len(result["daily_forecast"]), 7)
        self.assertIsNotNone(result["validation"]["mape"])


if __name__ == "__main__":
    unittest.main()
