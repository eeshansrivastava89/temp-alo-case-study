"""Read-only SQLite repository with validated metric and period queries."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterator

from .semantic_model import Metric, get_metric, validate_dimension


@dataclass(frozen=True)
class Period:
    id: str
    label: str
    start: str
    end: str

    @property
    def days(self) -> int:
        return (date.fromisoformat(self.end) - date.fromisoformat(self.start)).days + 1


class AnalyticsRepository:
    def __init__(self, database_path: str | Path):
        self.path = Path(database_path).resolve()
        if not self.path.exists():
            raise FileNotFoundError(f"Analytics database not found: {self.path}")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")
        try:
            yield connection
        finally:
            connection.close()

    def data_through(self) -> str:
        with self.connect() as connection:
            return connection.execute("SELECT MAX(date) FROM dim_date").fetchone()[0]

    def source_inventory(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            tables = [
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'fact_%' ORDER BY name"
                )
            ]
            inventory = []
            for table in tables:
                row = connection.execute(
                    f"""SELECT
                            COUNT(*) AS rows,
                            MIN(date) AS date_min,
                            MAX(date) AS date_max,
                            MIN(source_file) AS source_file,
                            MIN(source_sheet) AS source_sheet
                        FROM {table}"""
                ).fetchone()
                inventory.append(
                    {
                        "source_file": row["source_file"],
                        "sheet": row["source_sheet"],
                        "fact_table": table,
                        "metric_view": f"vw_{table.removeprefix('fact_')}_metrics",
                        "rows": row["rows"],
                        "date_min": row["date_min"],
                        "date_max": row["date_max"],
                    }
                )
            return inventory

    def database_objects(self) -> list[str]:
        with self.connect() as connection:
            return [
                row["name"]
                for row in connection.execute(
                    """SELECT name FROM sqlite_master
                       WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'
                       ORDER BY type, name"""
                )
            ]

    def object_schema(self, object_name: str) -> list[dict[str, Any]]:
        if object_name not in self.database_objects():
            raise ValueError(f"Unknown database object: {object_name}")
        with self.connect() as connection:
            return [
                {"position": row["cid"] + 1, "column": row["name"], "type": row["type"] or "derived"}
                for row in connection.execute(f"PRAGMA table_info({object_name})")
            ]

    def resolve_period(self, period_id: str = "latest_complete_week") -> Period:
        with self.connect() as connection:
            if period_id == "latest_complete_week":
                row = connection.execute(
                    """SELECT week_start, week_end FROM dim_date
                       WHERE is_complete_week = 1 ORDER BY week_end DESC LIMIT 1"""
                ).fetchone()
                return Period(period_id, f"Week of {row['week_start']} to {row['week_end']}", row["week_start"], row["week_end"])

            if period_id == "previous_complete_week":
                row = connection.execute(
                    """SELECT week_start, week_end FROM dim_date
                       WHERE is_complete_week = 1
                       GROUP BY week_start, week_end ORDER BY week_end DESC LIMIT 1 OFFSET 1"""
                ).fetchone()
                return Period(period_id, f"Week of {row['week_start']} to {row['week_end']}", row["week_start"], row["week_end"])

            if period_id == "latest_7_days":
                end = date.fromisoformat(self.data_through())
                start = end - timedelta(days=6)
                return Period(period_id, f"Latest 7 days: {start} to {end}", start.isoformat(), end.isoformat())

            if period_id == "latest_complete_month":
                row = connection.execute(
                    """SELECT calendar_month_start, calendar_month_end, calendar_month_name, calendar_year
                       FROM dim_date WHERE is_complete_month = 1
                       ORDER BY calendar_month_end DESC LIMIT 1"""
                ).fetchone()
                return Period(period_id, f"{row['calendar_month_name']} {row['calendar_year']}", row["calendar_month_start"], row["calendar_month_end"])

        raise ValueError(f"Unknown or unavailable period: {period_id}")

    @staticmethod
    def previous_period(period: Period) -> Period:
        start = date.fromisoformat(period.start)
        previous_end = start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=period.days - 1)
        return Period("previous_period", f"{previous_start} to {previous_end}", previous_start.isoformat(), previous_end.isoformat())

    @staticmethod
    def _expression(metric: Metric, use_ly: bool = False) -> str:
        if metric.is_ratio:
            numerator = metric.numerator_ly if use_ly else metric.numerator_ty
            denominator = metric.denominator_ly if use_ly else metric.denominator_ty
            return f"SUM({numerator}) / NULLIF(SUM({denominator}), 0)"
        column = metric.ly_column if use_ly else metric.ty_column
        return f"SUM({column})"

    def metric_value(self, metric_id: str, period: Period, *, use_ly: bool = False) -> float | None:
        metric = get_metric(metric_id)
        expression = self._expression(metric, use_ly)
        sql = f"SELECT {expression} AS value FROM {metric.view} WHERE date BETWEEN ? AND ?"
        with self.connect() as connection:
            value = connection.execute(sql, (period.start, period.end)).fetchone()["value"]
        return float(value) if value is not None else None

    def metric_by_dimension(
        self,
        metric_id: str,
        dimension: str,
        period: Period,
        *,
        use_ly: bool = False,
    ) -> list[dict[str, Any]]:
        metric = get_metric(metric_id)
        column = validate_dimension(metric.context, dimension)
        expression = self._expression(metric, use_ly)
        sql = f"""
            SELECT {column} AS dimension_value, {expression} AS value
            FROM {metric.view}
            WHERE date BETWEEN ? AND ?
            GROUP BY {column}
        """
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, (period.start, period.end))]

    def daily_metric(self, metric_id: str, *, use_ly: bool = False) -> list[dict[str, Any]]:
        metric = get_metric(metric_id)
        expression = self._expression(metric, use_ly)
        sql = f"SELECT date, {expression} AS value FROM {metric.view} GROUP BY date ORDER BY date"
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql)]

    def store_operating_metrics(self, period: Period) -> list[dict[str, Any]]:
        sql = """
            SELECT
                store_id,
                MIN(opening_date) AS opening_date,
                SUM(store_revenue_ty) AS revenue,
                SUM(store_traffic_ty) AS traffic,
                SUM(store_orders_ty) AS orders,
                SUM(store_units_ty) AS units
            FROM vw_retail_store_metrics
            WHERE date BETWEEN ? AND ?
            GROUP BY store_id
        """
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, (period.start, period.end))]
