#!/usr/bin/env python3
"""Build the read-only SQLite analytics database from the supplied workbooks."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

UNKNOWN = "Unknown"

SOURCE_FILES = {
    "digital_commerce": "Digital Daily-Country-State level - Transformed (v3).xlsx",
    "digital_marketing": "Digital-DailyxStatexChannelxDevice - Transformed (Top20) - v3.xlsx",
    "retail_store": "Retail - Daily & Store Level - Transformed (v3).xlsx",
    "retail_category": "Retail Product Category - Transformed (v3).xlsx",
}

SOURCE_SHEETS = {
    "digital_commerce": "digitaldailystate",
    "digital_marketing": "top 20 countries",
    "retail_store": "retaildailystore",
    "retail_category": "Sheet1",
}


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=root / "Case Study Data ")
    parser.add_argument("--output", type=Path, default=root / "data" / "analytics.db")
    return parser.parse_args()


def read_source(data_dir: Path, source: str) -> pd.DataFrame:
    path = data_dir / SOURCE_FILES[source]
    if not path.exists():
        raise FileNotFoundError(f"Missing source workbook: {path}")

    frame = pd.read_excel(path, sheet_name=SOURCE_SHEETS[source])
    frame["source_file"] = SOURCE_FILES[source]
    frame["source_sheet"] = SOURCE_SHEETS[source]
    frame["source_row_number"] = np.arange(2, len(frame) + 2, dtype=np.int64)
    return frame


def iso_date(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="raise")
    return parsed.dt.strftime("%Y-%m-%d")


def clean_dimension(series: pd.Series) -> pd.Series:
    values = series.astype("string").str.strip()
    values = values.mask(values.isna() | values.str.lower().isin(["(not-set)", "not set", "unknown", ""]), UNKNOWN)
    return values


def clean_digital_commerce(raw: pd.DataFrame) -> pd.DataFrame:
    renamed = raw.rename(
        columns={
            "ty_order_date": "date",
            "ty_fiscal_year": "fiscal_year",
            "ty_fiscal_month": "fiscal_month",
            "ty_total_revenue": "digital_revenue_ty",
            "ly_total_revenue": "digital_revenue_ly",
            "ty_total_units": "digital_units_ty",
            "ly_total_units": "digital_units_ly",
            "ty_total_orders": "digital_orders_ty",
            "ly_total_orders": "digital_orders_ly",
            "ty_new_customers": "digital_customers_acquired_ty",
            "ly_new_customers": "digital_customers_acquired_ly",
            "ty_sessions": "digital_sessions_ty",
            "ly_sessions": "digital_sessions_ly",
        }
    ).copy()
    renamed["date"] = iso_date(renamed["date"])
    geography_fields = ["country", "state_code", "state"]
    renamed["has_unknown_geography"] = renamed[geography_fields].isna().any(axis=1).astype("int8")
    for field in geography_fields:
        renamed[field] = clean_dimension(renamed[field])
    return renamed[
        [
            "date",
            "fiscal_year",
            "fiscal_month",
            "country",
            "state_code",
            "state",
            "has_unknown_geography",
            "digital_revenue_ty",
            "digital_revenue_ly",
            "digital_units_ty",
            "digital_units_ly",
            "digital_orders_ty",
            "digital_orders_ly",
            "digital_customers_acquired_ty",
            "digital_customers_acquired_ly",
            "digital_sessions_ty",
            "digital_sessions_ly",
            "source_file",
            "source_sheet",
            "source_row_number",
        ]
    ]


def clean_digital_marketing(raw: pd.DataFrame) -> pd.DataFrame:
    renamed = raw.rename(
        columns={
            "ty_date_dt": "date",
            "country_name": "country",
            "session_state": "state",
            "device_category": "device",
            "ty_ga_revenue": "ga_revenue_ty",
            "ly_ga_revenue": "ga_revenue_ly",
            "ty_sessions": "ga_sessions_ty",
            "ly_sessions": "ga_sessions_ly",
            "ty_total_orders": "ga_orders_ty",
            "ly_total_orders": "ga_orders_ly",
            "ty_digital_customers_acquired": "ga_customers_acquired_ty",
            "ly_digital_customers_acquired": "ga_customers_acquired_ly",
            "ty_qty_ordered": "ga_units_ty",
            "ly_qty_ordered": "ga_units_ly",
        }
    ).copy()
    renamed["date"] = iso_date(renamed["date"])
    dimension_fields = ["channel", "country", "state", "device"]
    raw_unknown = renamed[dimension_fields].astype("string").apply(
        lambda column: column.str.strip().str.lower().isin(["(not-set)", "not set", "unknown", ""])
    )
    renamed["has_unknown_dimension"] = raw_unknown.any(axis=1).astype("int8")
    for field in dimension_fields:
        renamed[field] = clean_dimension(renamed[field])
    return renamed[
        [
            "date",
            "channel",
            "country",
            "state",
            "device",
            "has_unknown_dimension",
            "ga_revenue_ty",
            "ga_revenue_ly",
            "ga_sessions_ty",
            "ga_sessions_ly",
            "ga_orders_ty",
            "ga_orders_ly",
            "ga_customers_acquired_ty",
            "ga_customers_acquired_ly",
            "ga_units_ty",
            "ga_units_ly",
            "source_file",
            "source_sheet",
            "source_row_number",
        ]
    ]


def clean_retail_store(raw: pd.DataFrame) -> pd.DataFrame:
    cleaned = raw.loc[raw["store_id"].ne(0)].rename(
        columns={
            "day": "date",
            "ty_net_sales": "store_revenue_ty",
            "ly_net_sales": "store_revenue_ly",
            "ty_traffic": "store_traffic_ty",
            "ly_traffic": "store_traffic_ly",
            "ty_orders": "store_orders_ty",
            "ly_orders": "store_orders_ly",
            "ty_units": "store_units_ty",
            "ly_units": "store_units_ly",
        }
    ).copy()
    cleaned["date"] = iso_date(cleaned["date"])
    cleaned["opening_date_missing"] = cleaned["opening_date"].isna().astype("int8")
    cleaned["opening_date"] = iso_date(cleaned["opening_date"]).where(cleaned["opening_date"].notna(), None)
    return cleaned[
        [
            "date",
            "store_id",
            "opening_date",
            "opening_date_missing",
            "store_revenue_ty",
            "store_revenue_ly",
            "store_traffic_ty",
            "store_traffic_ly",
            "store_orders_ty",
            "store_orders_ly",
            "store_units_ty",
            "store_units_ly",
            "source_file",
            "source_sheet",
            "source_row_number",
        ]
    ]


def clean_retail_category(raw: pd.DataFrame) -> pd.DataFrame:
    cleaned = raw.rename(
        columns={
            "day": "date",
            "ty_net_sales": "category_revenue_ty",
            "ly_net_sales": "category_revenue_ly",
            "ty_units": "category_units_ty",
            "ly_units": "category_units_ly",
        }
    ).copy()
    cleaned["date"] = iso_date(cleaned["date"])
    cleaned["opening_date"] = iso_date(cleaned["opening_date"])
    cleaned["product_category"] = clean_dimension(cleaned["product_category"])
    cleaned["metrics_approved"] = 0
    cleaned["restriction_reason"] = "Blocked pending reconciliation with store totals"
    return cleaned[
        [
            "date",
            "store_id",
            "product_category",
            "opening_date",
            "category_revenue_ty",
            "category_revenue_ly",
            "category_units_ty",
            "category_units_ly",
            "metrics_approved",
            "restriction_reason",
            "source_file",
            "source_sheet",
            "source_row_number",
        ]
    ]


CLEANERS: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "digital_commerce": clean_digital_commerce,
    "digital_marketing": clean_digital_marketing,
    "retail_store": clean_retail_store,
    "retail_category": clean_retail_category,
}

TABLE_NAMES = {
    "digital_commerce": "fact_digital_commerce",
    "digital_marketing": "fact_digital_marketing",
    "retail_store": "fact_retail_store",
    "retail_category": "fact_retail_category",
}


def build_date_dimension(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    all_dates = pd.concat([frame["date"] for frame in frames.values()], ignore_index=True)
    dates = pd.date_range(all_dates.min(), all_dates.max(), freq="D")
    dim = pd.DataFrame({"date_value": dates})
    dim["date"] = dim["date_value"].dt.strftime("%Y-%m-%d")
    dim["calendar_year"] = dim["date_value"].dt.year
    dim["calendar_month"] = dim["date_value"].dt.month
    dim["calendar_month_name"] = dim["date_value"].dt.month_name()
    dim["calendar_month_start"] = dim["date_value"].dt.to_period("M").dt.start_time.dt.strftime("%Y-%m-%d")
    dim["calendar_month_end"] = dim["date_value"].dt.to_period("M").dt.end_time.dt.strftime("%Y-%m-%d")
    dim["day_of_week"] = dim["date_value"].dt.dayofweek + 1
    dim["day_name"] = dim["date_value"].dt.day_name()
    dim["week_start"] = (dim["date_value"] - pd.to_timedelta(dim["date_value"].dt.dayofweek, unit="D")).dt.strftime("%Y-%m-%d")
    dim["week_end"] = (pd.to_datetime(dim["week_start"]) + pd.Timedelta(days=6)).dt.strftime("%Y-%m-%d")

    data_min = dim["date_value"].min()
    data_max = dim["date_value"].max()
    dim["is_complete_week"] = (
        (pd.to_datetime(dim["week_start"]) >= data_min)
        & (pd.to_datetime(dim["week_end"]) <= data_max)
    ).astype("int8")
    dim["is_complete_month"] = (
        (pd.to_datetime(dim["calendar_month_start"]) >= data_min)
        & (pd.to_datetime(dim["calendar_month_end"]) <= data_max)
    ).astype("int8")

    fiscal = (
        frames["digital_commerce"][["date", "fiscal_year", "fiscal_month"]]
        .drop_duplicates()
    )
    if fiscal["date"].duplicated().any():
        raise ValueError("A date maps to more than one supplied fiscal period")
    dim = dim.merge(fiscal, on="date", how="left", validate="one_to_one")
    return dim.drop(columns="date_value")


def create_indexes(connection: sqlite3.Connection) -> None:
    statements = [
        "CREATE UNIQUE INDEX idx_dim_date_date ON dim_date(date)",
        "CREATE INDEX idx_digital_commerce_date ON fact_digital_commerce(date)",
        "CREATE INDEX idx_digital_commerce_geo ON fact_digital_commerce(country, state)",
        "CREATE INDEX idx_digital_marketing_date ON fact_digital_marketing(date)",
        "CREATE INDEX idx_digital_marketing_channel_device ON fact_digital_marketing(channel, device)",
        "CREATE INDEX idx_digital_marketing_geo ON fact_digital_marketing(country, state)",
        "CREATE UNIQUE INDEX idx_retail_store_grain ON fact_retail_store(date, store_id)",
        "CREATE INDEX idx_retail_store_store ON fact_retail_store(store_id)",
        "CREATE UNIQUE INDEX idx_retail_category_grain ON fact_retail_category(date, store_id, product_category)",
        "CREATE INDEX idx_retail_category_store_category ON fact_retail_category(store_id, product_category)",
    ]
    for statement in statements:
        connection.execute(statement)


def create_views(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE VIEW vw_digital_commerce_metrics AS
        SELECT
            f.*,
            d.calendar_year,
            d.calendar_month,
            d.calendar_month_name,
            d.day_of_week,
            d.day_name,
            d.week_start,
            d.week_end,
            d.is_complete_week,
            d.is_complete_month
        FROM fact_digital_commerce AS f
        JOIN dim_date AS d USING (date);

        CREATE VIEW vw_digital_marketing_metrics AS
        SELECT
            f.*,
            d.calendar_year,
            d.calendar_month,
            d.calendar_month_name,
            d.day_of_week,
            d.day_name,
            d.week_start,
            d.week_end,
            d.is_complete_week,
            d.is_complete_month
        FROM fact_digital_marketing AS f
        JOIN dim_date AS d USING (date);

        CREATE VIEW vw_retail_store_metrics AS
        SELECT
            f.*,
            d.calendar_year,
            d.calendar_month,
            d.calendar_month_name,
            d.day_of_week,
            d.day_name,
            d.week_start,
            d.week_end,
            d.is_complete_week,
            d.is_complete_month,
            CASE
                WHEN f.opening_date IS NULL THEN 'Unknown opening date'
                WHEN f.opening_date > date(f.date, '-1 year') THEN 'New / no LY baseline'
                WHEN f.store_revenue_ly = 0
                 AND f.store_traffic_ly = 0
                 AND f.store_orders_ly = 0
                 AND f.store_units_ly = 0 THEN 'Existing store with no LY activity'
                ELSE 'Comparable store'
            END AS ly_baseline_status
        FROM fact_retail_store AS f
        JOIN dim_date AS d USING (date);

        CREATE VIEW vw_retail_category_metrics AS
        SELECT
            f.*,
            d.calendar_year,
            d.calendar_month,
            d.calendar_month_name,
            d.day_of_week,
            d.day_name,
            d.week_start,
            d.week_end,
            d.is_complete_week,
            d.is_complete_month
        FROM fact_retail_category AS f
        JOIN dim_date AS d USING (date);
        """
    )


def validate_before_write(raw: dict[str, pd.DataFrame], clean: dict[str, pd.DataFrame]) -> list[str]:
    checks: list[str] = []

    for source in ["digital_commerce", "digital_marketing", "retail_category"]:
        assert len(clean[source]) == len(raw[source]), f"Unexpected row loss in {source}"
        checks.append(f"PASS row preservation: {source} ({len(clean[source]):,})")

    placeholders = int(raw["retail_store"]["store_id"].eq(0).sum())
    assert placeholders > 0, "Expected Retail placeholder rows were not found"
    assert len(clean["retail_store"]) == len(raw["retail_store"]) - placeholders
    assert not clean["retail_store"]["store_id"].eq(0).any()
    checks.append(f"PASS placeholder removal: retail_store ({placeholders:,} rows removed)")

    known_geo = clean["digital_commerce"].loc[clean["digital_commerce"]["has_unknown_geography"].eq(0)]
    assert not known_geo.duplicated(["date", "country", "state_code", "state"]).any()
    checks.append("PASS known Digital commerce geography is unique at its reporting grain")

    assert not clean["digital_marketing"].duplicated(["date", "channel", "country", "state", "device"]).any()
    checks.append("PASS Digital marketing reporting grain is unique")

    assert not clean["retail_store"].duplicated(["date", "store_id"]).any()
    checks.append("PASS Retail store reporting grain is unique")

    assert not clean["retail_category"].duplicated(["date", "store_id", "product_category"]).any()
    checks.append("PASS Retail category reporting grain is unique")

    assert clean["retail_category"]["metrics_approved"].eq(0).all()
    checks.append("PASS Retail category metrics remain restricted")

    return checks


def validate_database(path: Path, expected_rows: dict[str, int], expected_dates: int) -> list[str]:
    checks: list[str] = []
    uri = f"file:{path.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        assert integrity == "ok", integrity
        checks.append("PASS SQLite integrity check")

        for source, expected in expected_rows.items():
            table = TABLE_NAMES[source]
            actual = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert actual == expected, f"{table}: expected {expected}, found {actual}"
            checks.append(f"PASS table row count: {table} ({actual:,})")

        date_count = connection.execute("SELECT COUNT(*) FROM dim_date").fetchone()[0]
        assert date_count == expected_dates
        checks.append(f"PASS date dimension row count ({date_count:,})")

        complete_weeks = connection.execute(
            "SELECT COUNT(DISTINCT week_start) FROM dim_date WHERE is_complete_week = 1"
        ).fetchone()[0]
        assert complete_weeks == 8, f"Expected 8 complete Monday-Sunday weeks, found {complete_weeks}"
        checks.append("PASS Monday-Sunday week contract (8 complete weeks)")

        views = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'view'"
            )
        }
        expected_views = {
            "vw_digital_commerce_metrics",
            "vw_digital_marketing_metrics",
            "vw_retail_store_metrics",
            "vw_retail_category_metrics",
        }
        assert views == expected_views, f"Unexpected views: {views}"
        checks.append("PASS metric views created")

    return checks


def build_database(data_dir: Path, output: Path) -> list[str]:
    raw = {source: read_source(data_dir, source) for source in SOURCE_FILES}
    clean = {source: CLEANERS[source](frame) for source, frame in raw.items()}
    checks = validate_before_write(raw, clean)
    dim_date = build_date_dimension(clean)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.db")
    temporary.unlink(missing_ok=True)

    try:
        with sqlite3.connect(temporary) as connection:
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute("PRAGMA foreign_keys = ON")
            for source, frame in clean.items():
                frame.to_sql(TABLE_NAMES[source], connection, index=False, if_exists="replace")
            dim_date.to_sql("dim_date", connection, index=False, if_exists="replace")
            create_indexes(connection)
            create_views(connection)
            connection.execute("ANALYZE")
            connection.commit()
            connection.execute("VACUUM")

        expected_rows = {source: len(frame) for source, frame in clean.items()}
        checks.extend(validate_database(temporary, expected_rows, len(dim_date)))
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return checks


def main() -> None:
    args = parse_args()
    checks = build_database(args.data_dir, args.output)
    print(f"Built {args.output} ({args.output.stat().st_size / 1024 / 1024:,.1f} MiB)")
    for check in checks:
        print(check)


if __name__ == "__main__":
    main()
