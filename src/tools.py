"""Deterministic analytical tools exposed to the AI orchestration layer."""

from __future__ import annotations

from itertools import permutations
from typing import Any

import numpy as np
import pandas as pd

from .repository import AnalyticsRepository, Period
from .semantic_model import CONTEXT_LABELS, SUMMARY_METRICS, get_metric

CONTEXT_NOTES = {
    "digital": "Digital commerce is the top-line source; unknown geography is retained in totals.",
    "ga": "GA metrics are diagnostic and do not reconcile exactly to Digital commerce totals.",
    "store": "Store Revenue maps to supplied net sales; negative values are retained as possible returns.",
}


def _comparison(repo: AnalyticsRepository, period: Period, comparison: str) -> tuple[Period, bool, str]:
    if comparison == "previous_period":
        if period.id == "full_available_period":
            raise ValueError("The full available period has no preceding matched window; use comparison='ly'")
        prior = repo.previous_period(period)
        return prior, False, prior.label
    if comparison == "ly":
        return period, True, "Supplied LY fields for the requested dates"
    raise ValueError("comparison must be 'previous_period' or 'ly'")


def _change(value: float | None, baseline: float | None) -> dict[str, float | None]:
    if value is None or baseline is None:
        return {"absolute": None, "percent": None}
    absolute = value - baseline
    percent = absolute / baseline if baseline != 0 else None
    return {"absolute": absolute, "percent": percent}


def get_performance_summary(
    repo: AnalyticsRepository,
    context: str,
    period: str = "latest_complete_week",
    comparison: str = "previous_period",
) -> dict[str, Any]:
    if context not in SUMMARY_METRICS:
        raise ValueError(f"Unknown context: {context}")
    current_period = repo.resolve_period(period)
    baseline_period, use_ly, baseline_label = _comparison(repo, current_period, comparison)
    results = []
    for metric_id in SUMMARY_METRICS[context]:
        metric = get_metric(metric_id)
        value = repo.metric_value(metric_id, current_period)
        baseline = repo.metric_value(metric_id, baseline_period, use_ly=use_ly)
        results.append(
            {
                "metric": metric_id,
                "label": metric.label,
                "format": metric.format,
                "value": value,
                "baseline": baseline,
                "change": _change(value, baseline),
            }
        )
    return {
        "tool": "get_performance_summary",
        "context": context,
        "context_label": CONTEXT_LABELS[context],
        "period": current_period.__dict__,
        "comparison": {"type": comparison, "label": baseline_label},
        "metrics": results,
        "notes": [CONTEXT_NOTES[context]],
    }


def _shapley_contributions(base: dict[str, float], current: dict[str, float]) -> dict[str, float]:
    names = list(base)
    contributions = dict.fromkeys(names, 0.0)
    all_orders = list(permutations(names))
    for order in all_orders:
        values = base.copy()
        before = float(np.prod(list(values.values())))
        for name in order:
            values[name] = current[name]
            after = float(np.prod(list(values.values())))
            contributions[name] += after - before
            before = after
    return {name: value / len(all_orders) for name, value in contributions.items()}


def analyze_revenue_drivers(
    repo: AnalyticsRepository,
    context: str,
    period: str = "latest_complete_week",
    comparison: str = "previous_period",
) -> dict[str, Any]:
    if context not in {"digital", "store"}:
        raise ValueError("Revenue drivers are available for 'digital' or 'store'")
    current_period = repo.resolve_period(period)
    baseline_period, use_ly, baseline_label = _comparison(repo, current_period, comparison)

    if context == "digital":
        factor_metrics = {"Orders": "digital_orders", "AOV": "digital_aov"}
        revenue_metric = "digital_revenue"
    else:
        factor_metrics = {
            "Traffic": "store_traffic",
            "Conversion": "store_conversion_rate",
            "AOV": "store_aov",
        }
        revenue_metric = "store_revenue"

    current = {name: repo.metric_value(metric_id, current_period) for name, metric_id in factor_metrics.items()}
    baseline = {
        name: repo.metric_value(metric_id, baseline_period, use_ly=use_ly)
        for name, metric_id in factor_metrics.items()
    }
    if any(value is None for value in [*current.values(), *baseline.values()]):
        raise ValueError("Driver decomposition has an unavailable factor")

    contributions = _shapley_contributions(baseline, current)  # type: ignore[arg-type]
    current_revenue = repo.metric_value(revenue_metric, current_period)
    baseline_revenue = repo.metric_value(revenue_metric, baseline_period, use_ly=use_ly)
    revenue_change = _change(current_revenue, baseline_revenue)
    ranked = sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)

    result: dict[str, Any] = {
        "tool": "analyze_revenue_drivers",
        "context": context,
        "context_label": CONTEXT_LABELS[context],
        "period": current_period.__dict__,
        "comparison": {"type": comparison, "label": baseline_label},
        "revenue": {"value": current_revenue, "baseline": baseline_revenue, "change": revenue_change},
        "factors": [
            {
                "factor": name,
                "value": current[name],
                "baseline": baseline[name],
                "change": _change(current[name], baseline[name]),
                "revenue_contribution": contribution,
            }
            for name, contribution in ranked
        ],
        "method": "Shapley decomposition; contributions add to the revenue change.",
        "notes": [CONTEXT_NOTES[context]],
    }

    if context == "digital":
        ga = get_performance_summary(repo, "ga", period, comparison)
        result["supporting_ga_diagnostics"] = ga["metrics"]
        result["notes"].append("GA signals provide supporting context and are not forced to reconcile to commerce revenue.")
    return result


def _store_profile(current: dict[str, Any], baseline: dict[str, Any]) -> list[dict[str, Any]]:
    def ratio(numerator: float | None, denominator: float | None) -> float | None:
        return float(numerator / denominator) if numerator is not None and denominator else None

    measures = [
        ("store_revenue", "Store Revenue", "currency", current.get("revenue"), baseline.get("revenue")),
        ("store_traffic", "Store Traffic", "integer", current.get("traffic"), baseline.get("traffic")),
        ("store_orders", "Store Orders", "integer", current.get("orders"), baseline.get("orders")),
        ("store_units", "Store Units", "integer", current.get("units"), baseline.get("units")),
        (
            "store_conversion_rate",
            "Store Conversion Rate",
            "percent",
            ratio(current.get("orders"), current.get("traffic")),
            ratio(baseline.get("orders"), baseline.get("traffic")),
        ),
        (
            "store_aov",
            "Store AOV",
            "currency",
            ratio(current.get("revenue"), current.get("orders")),
            ratio(baseline.get("revenue"), baseline.get("orders")),
        ),
        (
            "store_upt",
            "Store UPT",
            "decimal",
            ratio(current.get("units"), current.get("orders")),
            ratio(baseline.get("units"), baseline.get("orders")),
        ),
    ]
    return [
        {"metric": metric, "label": label, "format": display_format, "value": value, "baseline": base, "change": _change(value, base)}
        for metric, label, display_format, value, base in measures
    ]


def rank_performance(
    repo: AnalyticsRepository,
    metric: str,
    dimension: str,
    period: str = "latest_complete_week",
    comparison: str = "previous_period",
    direction: str = "bottom",
    ranking_basis: str = "change",
    limit: int = 8,
) -> dict[str, Any]:
    if ranking_basis not in {"value", "change"}:
        raise ValueError("ranking_basis must be 'value' or 'change'")
    definition = get_metric(metric)
    current_period = repo.resolve_period(period)
    baseline_period, use_ly, baseline_label = _comparison(repo, current_period, comparison)
    current = {str(row["dimension_value"]): row["value"] for row in repo.metric_by_dimension(metric, dimension, current_period)}
    baseline = {
        str(row["dimension_value"]): row["value"]
        for row in repo.metric_by_dimension(metric, dimension, baseline_period, use_ly=use_ly)
    }
    rows = []
    for key in current.keys() | baseline.keys():
        value = float(current.get(key) or 0)
        base = float(baseline.get(key) or 0)
        rows.append({"dimension_value": key, "value": value, "baseline": base, "change": _change(value, base)})
    reverse = direction == "top"
    if ranking_basis == "value":
        rows.sort(key=lambda row: row["value"], reverse=reverse)
    else:
        rows.sort(key=lambda row: row["change"]["absolute"] or 0, reverse=reverse)
    selected = rows[: max(1, min(limit, 20))]

    if dimension == "store":
        current_profiles = {
            str(row["store_id"]): row for row in repo.store_operating_metrics(current_period)
        }
        baseline_profiles = {
            str(row["store_id"]): row for row in repo.store_operating_metrics(baseline_period, use_ly=use_ly)
        }
        for row in selected:
            store_id = row["dimension_value"]
            row["profile"] = _store_profile(
                current_profiles.get(store_id, {}), baseline_profiles.get(store_id, {})
            )

    return {
        "tool": "rank_performance",
        "metric": metric,
        "metric_label": definition.label,
        "metric_format": definition.format,
        "dimension": dimension,
        "direction": direction,
        "ranking_basis": ranking_basis,
        "entities_evaluated": len(rows),
        "period": current_period.__dict__,
        "comparison": {"type": comparison, "label": baseline_label},
        "results": selected,
        "notes": [CONTEXT_NOTES[definition.context]],
    }


def diagnose_stores(
    repo: AnalyticsRepository,
    period: str = "latest_complete_week",
    comparison: str = "previous_period",
    limit: int = 8,
) -> dict[str, Any]:
    if comparison != "previous_period":
        raise ValueError("Store diagnosis currently uses the previous matched period")
    current_period = repo.resolve_period(period)
    prior_period = repo.previous_period(current_period)
    current = {row["store_id"]: row for row in repo.store_operating_metrics(current_period)}
    prior = {row["store_id"]: row for row in repo.store_operating_metrics(prior_period)}
    findings = []

    actions = {
        "Traffic": "Review local demand, operating hours, and traffic-driving activity.",
        "Conversion": "Review staffing, service, and in-store availability.",
        "AOV": "Review product mix, attachment, and markdown activity.",
    }
    for store_id in current.keys() & prior.keys():
        now, before = current[store_id], prior[store_id]
        if not before["traffic"] or not before["orders"] or not now["traffic"] or not now["orders"]:
            continue
        current_factors = {
            "Traffic": float(now["traffic"]),
            "Conversion": float(now["orders"] / now["traffic"]),
            "AOV": float(now["revenue"] / now["orders"]),
        }
        prior_factors = {
            "Traffic": float(before["traffic"]),
            "Conversion": float(before["orders"] / before["traffic"]),
            "AOV": float(before["revenue"] / before["orders"]),
        }
        contributions = _shapley_contributions(prior_factors, current_factors)
        primary_driver = min(contributions, key=contributions.get)
        delta = float(now["revenue"] - before["revenue"])
        findings.append(
            {
                "store_id": int(store_id),
                "revenue": float(now["revenue"]),
                "revenue_change": {"absolute": delta, "percent": delta / before["revenue"] if before["revenue"] else None},
                "primary_driver": primary_driver,
                "driver_contribution": contributions[primary_driver],
                "recommended_check": actions[primary_driver],
            }
        )

    findings.sort(key=lambda row: row["revenue_change"]["absolute"])
    selected = findings[: max(1, min(limit, 20))]
    portfolio_revenue = sum(float(row["revenue"]) for row in current.values())
    portfolio_baseline = sum(float(row["revenue"]) for row in prior.values())
    portfolio_change = portfolio_revenue - portfolio_baseline
    selected_decline = sum(min(0.0, row["revenue_change"]["absolute"]) for row in selected)
    return {
        "tool": "diagnose_stores",
        "period": current_period.__dict__,
        "comparison": {"type": comparison, "label": prior_period.label},
        "portfolio": {
            "metric": "store_revenue",
            "label": "Store Revenue",
            "value": portfolio_revenue,
            "baseline": portfolio_baseline,
            "change": _change(portfolio_revenue, portfolio_baseline),
        },
        "attention_group": {
            "stores_returned": len(selected),
            "gross_store_revenue_decline": selected_decline,
            "offset_from_other_stores": portfolio_change - selected_decline,
        },
        "stores": selected,
        "method": "Stores ranked by absolute Store Revenue decline; operating driver uses Shapley decomposition.",
        "notes": [CONTEXT_NOTES["store"]],
    }


def _seasonal_median_predictions(history: pd.DataFrame, forecast_dates: pd.Series, lookback_weeks: int = 4) -> np.ndarray:
    predictions = []
    for forecast_date in forecast_dates:
        same_weekday = history.loc[history["date"].dt.dayofweek.eq(forecast_date.dayofweek), "value"].tail(lookback_weeks)
        if same_weekday.empty:
            raise ValueError("Insufficient weekday history for forecast")
        predictions.append(float(same_weekday.median()))
    return np.asarray(predictions)


def forecast_metric(
    repo: AnalyticsRepository,
    metric: str,
    horizon_days: int = 7,
) -> dict[str, Any]:
    definition = get_metric(metric)
    if definition.is_ratio:
        raise ValueError("Forecasting is limited to additive metrics")
    horizon_days = max(1, min(int(horizon_days), 31))
    history = pd.DataFrame(repo.daily_metric(metric))
    history["date"] = pd.to_datetime(history["date"])
    history["value"] = pd.to_numeric(history["value"])
    if len(history) < 35:
        raise ValueError("At least five weeks of daily observations are required")

    validation_days = 7
    train, holdout = history.iloc[:-validation_days], history.iloc[-validation_days:]
    holdout_pred = _seasonal_median_predictions(train, holdout["date"])
    residuals = holdout["value"].to_numpy() - holdout_pred
    holdout_mae = float(np.mean(np.abs(residuals)))
    holdout_mape = float(np.mean(np.abs(residuals / holdout["value"].to_numpy()))) if (holdout["value"] != 0).all() else None

    future_dates = pd.Series(pd.date_range(history["date"].max() + pd.Timedelta(days=1), periods=horizon_days))
    predictions = _seasonal_median_predictions(history, future_dates)
    forecast_total = float(predictions.sum())
    interval = 1.96 * float(np.std(residuals, ddof=1)) * np.sqrt(horizon_days)
    baseline = history.iloc[-horizon_days:]
    baseline_total = float(baseline["value"].sum())
    baseline_start = baseline["date"].iloc[0].date().isoformat()
    baseline_end = baseline["date"].iloc[-1].date().isoformat()

    return {
        "tool": "forecast_metric",
        "metric": metric,
        "metric_label": definition.label,
        "forecast_period": {"start": future_dates.iloc[0].date().isoformat(), "end": future_dates.iloc[-1].date().isoformat()},
        "forecast_total": forecast_total,
        "baseline_period": {
            "start": baseline_start,
            "end": baseline_end,
            "days": horizon_days,
            "label": f"Observed prior {horizon_days} days: {baseline_start} to {baseline_end}",
        },
        "recent_baseline_total": baseline_total,
        "change_vs_recent": _change(forecast_total, baseline_total),
        "interval_95_approx": {"lower": max(0, forecast_total - interval), "upper": forecast_total + interval},
        "validation": {"holdout_days": validation_days, "mae": holdout_mae, "mape": holdout_mape},
        "daily_forecast": [
            {"date": day.date().isoformat(), "value": float(value)}
            for day, value in zip(future_dates, predictions, strict=True)
        ],
        "method": "Each forecast day is the median of the prior four observations for that weekday; the comparison baseline is the observed total for the immediately preceding matched days, and the latest seven observed days are also held out for validation.",
        "notes": [
            CONTEXT_NOTES[definition.context],
            "Directional prototype forecast; promotions, inventory, spend, holidays, weather, and market plans are unavailable.",
        ],
    }


TOOL_FUNCTIONS = {
    "get_performance_summary": get_performance_summary,
    "analyze_revenue_drivers": analyze_revenue_drivers,
    "rank_performance": rank_performance,
    "diagnose_stores": diagnose_stores,
    "forecast_metric": forecast_metric,
}


def dispatch_tool(repo: AnalyticsRepository, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        function = TOOL_FUNCTIONS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown tool: {name}") from exc
    return function(repo, **arguments)
