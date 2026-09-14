"""Governed metric and dimension definitions used by every analytical tool."""

from dataclasses import dataclass
from typing import Literal

Format = Literal["currency", "integer", "decimal", "percent"]


@dataclass(frozen=True)
class Metric:
    id: str
    label: str
    context: str
    view: str
    ty_column: str | None = None
    ly_column: str | None = None
    numerator_ty: str | None = None
    numerator_ly: str | None = None
    denominator_ty: str | None = None
    denominator_ly: str | None = None
    format: Format = "decimal"
    description: str = ""

    @property
    def is_ratio(self) -> bool:
        return self.numerator_ty is not None


CONTEXT_VIEWS = {
    "digital": "vw_digital_commerce_metrics",
    "ga": "vw_digital_marketing_metrics",
    "store": "vw_retail_store_metrics",
}

CONTEXT_LABELS = {
    "digital": "Digital Commerce",
    "ga": "GA Diagnostics",
    "store": "Retail Stores",
}

DIMENSIONS = {
    "digital": {
        "country": "country",
        "state": "state",
    },
    "ga": {
        "channel": "channel",
        "country": "country",
        "state": "state",
        "device": "device",
    },
    "store": {
        "store": "store_id",
        "ly_baseline_status": "ly_baseline_status",
    },
}


def additive(metric_id: str, label: str, context: str, ty: str, ly: str, fmt: Format, description: str = "") -> Metric:
    return Metric(metric_id, label, context, CONTEXT_VIEWS[context], ty_column=ty, ly_column=ly, format=fmt, description=description)


def ratio(metric_id: str, label: str, context: str, numerator: str, denominator: str, numerator_ly: str, denominator_ly: str, fmt: Format, description: str = "") -> Metric:
    return Metric(
        metric_id,
        label,
        context,
        CONTEXT_VIEWS[context],
        numerator_ty=numerator,
        numerator_ly=numerator_ly,
        denominator_ty=denominator,
        denominator_ly=denominator_ly,
        format=fmt,
        description=description,
    )


METRICS = {
    # Canonical Digital commerce metrics.
    "digital_revenue": additive("digital_revenue", "Digital Revenue", "digital", "digital_revenue_ty", "digital_revenue_ly", "currency"),
    "digital_orders": additive("digital_orders", "Digital Orders", "digital", "digital_orders_ty", "digital_orders_ly", "integer"),
    "digital_units": additive("digital_units", "Digital Units", "digital", "digital_units_ty", "digital_units_ly", "integer"),
    "digital_customers_acquired": additive("digital_customers_acquired", "Customers Acquired", "digital", "digital_customers_acquired_ty", "digital_customers_acquired_ly", "integer"),
    "digital_aov": ratio("digital_aov", "Digital AOV", "digital", "digital_revenue_ty", "digital_orders_ty", "digital_revenue_ly", "digital_orders_ly", "currency"),
    "digital_upt": ratio("digital_upt", "Digital UPT", "digital", "digital_units_ty", "digital_orders_ty", "digital_units_ly", "digital_orders_ly", "decimal"),
    # GA metrics remain explicitly prefixed and diagnostic.
    "ga_revenue": additive("ga_revenue", "GA Revenue", "ga", "ga_revenue_ty", "ga_revenue_ly", "currency", "GA-attributed revenue; not the Digital top-line source."),
    "ga_sessions": additive("ga_sessions", "GA Sessions", "ga", "ga_sessions_ty", "ga_sessions_ly", "integer"),
    "ga_orders": additive("ga_orders", "GA Orders", "ga", "ga_orders_ty", "ga_orders_ly", "integer"),
    "ga_units": additive("ga_units", "GA Units", "ga", "ga_units_ty", "ga_units_ly", "integer"),
    "ga_customers_acquired": additive("ga_customers_acquired", "GA Customers Acquired", "ga", "ga_customers_acquired_ty", "ga_customers_acquired_ly", "integer"),
    "ga_conversion_rate": ratio("ga_conversion_rate", "GA Conversion Rate", "ga", "ga_orders_ty", "ga_sessions_ty", "ga_orders_ly", "ga_sessions_ly", "percent"),
    "ga_aov": ratio("ga_aov", "GA AOV", "ga", "ga_revenue_ty", "ga_orders_ty", "ga_revenue_ly", "ga_orders_ly", "currency"),
    # Canonical Retail store metrics.
    "store_revenue": additive("store_revenue", "Store Revenue", "store", "store_revenue_ty", "store_revenue_ly", "currency", "Source field is Retail net sales."),
    "store_traffic": additive("store_traffic", "Store Traffic", "store", "store_traffic_ty", "store_traffic_ly", "integer"),
    "store_orders": additive("store_orders", "Store Orders", "store", "store_orders_ty", "store_orders_ly", "integer"),
    "store_units": additive("store_units", "Store Units", "store", "store_units_ty", "store_units_ly", "integer"),
    "store_conversion_rate": ratio("store_conversion_rate", "Store Conversion Rate", "store", "store_orders_ty", "store_traffic_ty", "store_orders_ly", "store_traffic_ly", "percent"),
    "store_aov": ratio("store_aov", "Store AOV", "store", "store_revenue_ty", "store_orders_ty", "store_revenue_ly", "store_orders_ly", "currency"),
    "store_upt": ratio("store_upt", "Store UPT", "store", "store_units_ty", "store_orders_ty", "store_units_ly", "store_orders_ly", "decimal"),
}

CONTEXT_METRICS = {
    context: tuple(metric_id for metric_id, metric in METRICS.items() if metric.context == context)
    for context in CONTEXT_VIEWS
}

SUMMARY_METRICS = {
    "digital": ("digital_revenue", "digital_orders", "digital_aov", "digital_customers_acquired"),
    "ga": ("ga_revenue", "ga_sessions", "ga_conversion_rate", "ga_aov"),
    "store": ("store_revenue", "store_traffic", "store_conversion_rate", "store_aov"),
}


def get_metric(metric_id: str) -> Metric:
    try:
        return METRICS[metric_id]
    except KeyError as exc:
        raise ValueError(f"Unknown metric: {metric_id}") from exc


def validate_dimension(context: str, dimension: str) -> str:
    try:
        return DIMENSIONS[context][dimension]
    except KeyError as exc:
        raise ValueError(f"Dimension {dimension!r} is not valid for {context!r}") from exc
