from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.repository import AnalyticsRepository
from src.tools import analyze_revenue_drivers, diagnose_stores, forecast_metric, get_performance_summary

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "analytics.db"

@st.cache_resource
def repository() -> AnalyticsRepository:
    return AnalyticsRepository(DB_PATH)


@st.cache_data(show_spinner=False)
def dashboard_data() -> dict:
    repo = repository()
    return {
        "digital": get_performance_summary(repo, "digital"),
        "ga": get_performance_summary(repo, "ga"),
        "store": get_performance_summary(repo, "store"),
        "digital_drivers": analyze_revenue_drivers(repo, "digital"),
        "store_drivers": analyze_revenue_drivers(repo, "store"),
        "stores": diagnose_stores(repo, limit=6),
        "digital_forecast": forecast_metric(repo, "digital_revenue"),
        "store_forecast": forecast_metric(repo, "store_revenue"),
    }


def money(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{sign}${magnitude / 1_000_000:.2f}M"
    if magnitude >= 1_000:
        return f"{sign}${magnitude / 1_000:.1f}K"
    return f"{sign}${magnitude:,.0f}"


def display_value(metric: dict) -> str:
    value = metric["value"]
    if value is None:
        return "n/a"
    if metric["format"] == "currency":
        return money(value)
    if metric["format"] == "percent":
        return f"{value:.1%}"
    return f"{value:,.0f}"


def display_delta(metric: dict) -> str:
    change = metric["change"]["percent"]
    return "No baseline" if change is None else f"{change:+.1%} vs prior week"


def render_metrics(summary: dict) -> None:
    columns = st.columns(len(summary["metrics"]))
    for column, metric in zip(columns, summary["metrics"], strict=True):
        column.metric(metric["label"], display_value(metric), display_delta(metric))


def driver_frame(result: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Driver": item["factor"], "Revenue contribution": item["revenue_contribution"]} for item in result["factors"]]
    ).set_index("Driver")


data = dashboard_data()
period = data["digital"]["period"]

st.title("Executive Dashboard")
st.caption(f"Latest complete week: {period['start']} to {period['end']} · Comparison: previous Monday–Sunday week")

st.header("Digital commerce")
render_metrics(data["digital"])
st.caption("Top-line Digital commerce source. Unknown geography remains in totals but is excluded from geographic claims.")

st.header("Retail stores")
render_metrics(data["store"])
st.caption("Store Revenue maps to supplied net sales. Negative values are retained as possible returns.")

st.divider()
left, right = st.columns(2)
with left:
    st.subheader("Digital revenue drivers")
    digital_change = data["digital_drivers"]["revenue"]["change"]
    st.metric("Revenue change", money(digital_change["absolute"]), f"{digital_change['percent']:+.1%}")
    st.bar_chart(driver_frame(data["digital_drivers"]), horizontal=True)
    ga_metrics = {item["metric"]: item for item in data["digital_drivers"]["supporting_ga_diagnostics"]}
    st.caption(
        f"Supporting GA diagnostics: sessions {ga_metrics['ga_sessions']['change']['percent']:+.1%}; "
        f"GA Conversion {ga_metrics['ga_conversion_rate']['change']['percent']:+.1%}. "
        "Traffic quality and tracking remain hypotheses to validate."
    )

with right:
    st.subheader("Store revenue drivers")
    store_change = data["store_drivers"]["revenue"]["change"]
    st.metric("Revenue change", money(store_change["absolute"]), f"{store_change['percent']:+.1%}")
    st.bar_chart(driver_frame(data["store_drivers"]), horizontal=True)
    st.caption("Shapley contributions reconcile to the revenue change. Conversion was the main pressure in this period.")

st.divider()
st.header("Stores requiring attention")
store_rows = [
    {
        "Store": str(item["store_id"]),
        "Revenue change": money(item["revenue_change"]["absolute"]),
        "Change %": f"{item['revenue_change']['percent']:+.1%}",
        "Primary driver": item["primary_driver"],
        "Recommended check": item["recommended_check"],
    }
    for item in data["stores"]["stores"]
]
st.dataframe(pd.DataFrame(store_rows), hide_index=True, width="stretch")

st.divider()
st.header("Directional seven-day forecast")
st.caption("Forecasts begin after the final observed date and use the immediately preceding seven observed days as the comparison baseline; this rolling window differs from the complete-week KPI period above.")
forecast_columns = st.columns(2)
for column, forecast in zip(forecast_columns, [data["digital_forecast"], data["store_forecast"]], strict=True):
    column.metric(
        forecast["metric_label"],
        money(forecast["forecast_total"]),
        f"{forecast['change_vs_recent']['percent']:+.1%} vs latest 7 days",
    )
    forecast_period = forecast["forecast_period"]
    baseline_period = forecast["baseline_period"]
    column.caption(
        f"Forecast: {forecast_period['start']} to {forecast_period['end']} · "
        f"Observed baseline: {baseline_period['start']} to {baseline_period['end']} "
        f"({money(forecast['recent_baseline_total'])}) · Four-week weekday median · "
        f"Holdout MAPE {forecast['validation']['mape']:.1%}"
    )

with st.expander("Data boundaries"):
    st.markdown(
        """
- GA metrics are diagnostic and are not forced to reconcile with Digital commerce.
- Retail category metrics are unavailable because they do not reconcile with Store Revenue.
- Combined Digital + Store revenue is unavailable without currency and gross-versus-net definitions.
- Forecasts exclude promotions, inventory, marketing spend, holidays, weather, and market plans.
"""
    )
