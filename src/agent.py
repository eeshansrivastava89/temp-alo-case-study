"""Optional OpenAI orchestration with a deterministic no-key demo fallback."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .repository import AnalyticsRepository
from .tools import (
    analyze_revenue_drivers,
    diagnose_stores,
    dispatch_tool,
    forecast_metric,
    get_performance_summary,
    rank_performance,
)


@dataclass
class AgentResponse:
    text: str
    evidence: list[dict[str, Any]]
    mode: str


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_performance_summary",
            "description": "Return governed KPIs for Digital commerce, GA diagnostics, or Retail stores.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {"type": "string", "enum": ["digital", "ga", "store"]},
                    "period": {"type": "string", "enum": ["latest_complete_week", "latest_7_days", "latest_complete_month"]},
                    "comparison": {"type": "string", "enum": ["previous_period", "ly"]},
                },
                "required": ["context"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_revenue_drivers",
            "description": "Quantify Digital Orders × AOV or Store Traffic × Conversion × AOV revenue drivers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {"type": "string", "enum": ["digital", "store"]},
                    "period": {"type": "string", "enum": ["latest_complete_week", "latest_7_days", "latest_complete_month"]},
                    "comparison": {"type": "string", "enum": ["previous_period", "ly"]},
                },
                "required": ["context"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rank_performance",
            "description": "Rank an approved geography, GA channel/device, or store dimension by metric change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["digital_revenue", "ga_revenue", "ga_sessions", "ga_conversion_rate", "store_revenue"]},
                    "dimension": {"type": "string", "enum": ["country", "state", "channel", "device", "store"]},
                    "period": {"type": "string", "enum": ["latest_complete_week", "latest_7_days", "latest_complete_month"]},
                    "comparison": {"type": "string", "enum": ["previous_period", "ly"]},
                    "direction": {"type": "string", "enum": ["top", "bottom"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["metric", "dimension"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_stores",
            "description": "Rank stores needing attention and identify the primary revenue driver.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["latest_complete_week", "latest_7_days"]},
                    "comparison": {"type": "string", "enum": ["previous_period"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forecast_metric",
            "description": "Forecast an approved additive KPI using a weekday seasonal baseline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["digital_revenue", "ga_revenue", "ga_sessions", "store_revenue", "store_traffic"]},
                    "horizon_days": {"type": "integer", "minimum": 1, "maximum": 14},
                },
                "required": ["metric"],
                "additionalProperties": False,
            },
        },
    },
]


def _money(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{sign}${magnitude / 1_000_000:.2f}M"
    if magnitude >= 1_000:
        return f"{sign}${magnitude / 1_000:.1f}K"
    return f"{sign}${magnitude:,.0f}"


def _percent(value: float | None, *, signed: bool = True) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.1%}" if signed else f"{value:.1%}"


def _metric_line(metric: dict[str, Any]) -> str:
    value = metric["value"]
    if metric["format"] == "currency":
        rendered = _money(value)
    elif metric["format"] == "percent":
        rendered = _percent(value, signed=False)
    else:
        rendered = f"{value:,.0f}" if value is not None else "n/a"
    return f"- **{metric['label']}:** {rendered} ({_percent(metric['change']['percent'])})"


def _demo_response(repo: AnalyticsRepository, prompt: str) -> AgentResponse:
    query = prompt.lower()
    evidence: list[dict[str, Any]] = []

    if "store" in query and any(word in query for word in ["attention", "risk", "which", "declin"]):
        result = diagnose_stores(repo, limit=5)
        evidence.append(result)
        lines = [
            f"### Stores requiring attention · {result['period']['start']} to {result['period']['end']}",
            "These stores had the largest absolute week-over-week revenue declines:",
        ]
        for store in result["stores"]:
            lines.append(
                f"- **Store {store['store_id']}:** {_money(store['revenue_change']['absolute'])} "
                f"({_percent(store['revenue_change']['percent'])}); primary driver: **{store['primary_driver']}**. "
                f"{store['recommended_check']}"
            )
        lines.append("\n*Start with these stores, then validate local inventory, hours, staffing, promotions, and market conditions before acting.*")
        return AgentResponse("\n".join(lines), evidence, "deterministic demo")

    if "forecast" in query or "next week" in query or "future" in query:
        digital = forecast_metric(repo, "digital_revenue")
        store = forecast_metric(repo, "store_revenue")
        evidence.extend([digital, store])
        text = f"""### Seven-day directional forecast

- **Digital Revenue:** {_money(digital['forecast_total'])}, {_percent(digital['change_vs_recent']['percent'])} versus the latest seven days. Holdout MAPE: {_percent(digital['validation']['mape'], signed=False)}.
- **Store Revenue:** {_money(store['forecast_total'])}, {_percent(store['change_vs_recent']['percent'])} versus the latest seven days. Holdout MAPE: {_percent(store['validation']['mape'], signed=False)}.

This seasonal baseline uses the median of the previous four observations for each weekday. Treat it as directional because promotions, inventory, marketing spend, holidays, weather, and market plans are unavailable."""
        return AgentResponse(text, evidence, "deterministic demo")

    if "channel" in query or "device" in query:
        dimension = "device" if "device" in query else "channel"
        direction = "bottom" if any(word in query for word in ["declin", "concern", "worst", "down"]) else "top"
        result = rank_performance(repo, "ga_revenue", dimension, direction=direction, limit=6)
        evidence.append(result)
        lines = [f"### GA Revenue by {dimension}", "GA is a diagnostic source and does not reconcile exactly to Digital commerce revenue."]
        for row in result["results"]:
            lines.append(f"- **{row['dimension_value']}:** {_money(row['value'])}; change {_money(row['change']['absolute'])} ({_percent(row['change']['percent'])})")
        return AgentResponse("\n".join(lines), evidence, "deterministic demo")

    if "why" in query or "driver" in query or "drove" in query:
        digital = analyze_revenue_drivers(repo, "digital")
        store = analyze_revenue_drivers(repo, "store")
        evidence.extend([digital, store])
        digital_factors = ", ".join(f"{f['factor']} {_money(f['revenue_contribution'])}" for f in digital["factors"])
        store_factors = ", ".join(f"{f['factor']} {_money(f['revenue_contribution'])}" for f in store["factors"])
        ga_metrics = {item["metric"]: item for item in digital["supporting_ga_diagnostics"]}
        text = f"""### Revenue driver readout · {digital['period']['start']} to {digital['period']['end']}

**Digital Revenue** changed {_money(digital['revenue']['change']['absolute'])} ({_percent(digital['revenue']['change']['percent'])}). The exact bridge is {digital_factors}. GA provides a supporting signal: sessions changed {_percent(ga_metrics['ga_sessions']['change']['percent'])}, while tracked conversion changed {_percent(ga_metrics['ga_conversion_rate']['change']['percent'])}. This could indicate traffic-quality pressure or a tracking gap; validate both before acting.

**Store Revenue** changed {_money(store['revenue']['change']['absolute'])} ({_percent(store['revenue']['change']['percent'])}). The bridge is {store_factors}. Conversion is the largest pressure, partly offset by AOV and traffic.

**Recommended next checks:** diagnose the stores with the largest conversion losses, then validate staffing, availability, and local conditions. Separately reconcile GA implementation and ecommerce events by market and device."""
        return AgentResponse(text, evidence, "deterministic demo")

    digital = get_performance_summary(repo, "digital")
    store = get_performance_summary(repo, "store")
    evidence.extend([digital, store])
    text = "\n".join(
        [
            f"### Weekly business pulse · {digital['period']['start']} to {digital['period']['end']}",
            "#### Digital Commerce",
            *[_metric_line(metric) for metric in digital["metrics"]],
            "#### Retail Stores",
            *[_metric_line(metric) for metric in store["metrics"]],
            "\n*Comparisons are against the previous complete Monday–Sunday week.*",
        ]
    )
    return AgentResponse(text, evidence, "deterministic demo")


def run_agent(
    repo: AnalyticsRepository,
    prompt: str,
    history: list[dict[str, str]] | None = None,
    *,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
) -> AgentResponse:
    if not api_key:
        return _demo_response(repo, prompt)

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    system = f"""You are an executive business analyst. Data is available through {repo.data_through()}.
Use tools for every numerical claim. Never calculate from memory or invent unavailable data.
Digital commerce is the top-line source; GA metrics must remain labeled GA and are diagnostic.
Retail category metrics and combined Digital + Store revenue are blocked.
Explain the period and comparison, quantify drivers, separate evidence from hypotheses, recommend validation before consequential action, and be concise.
Valid rank pairs: digital_revenue with country/state; ga_revenue or ga_sessions or ga_conversion_rate with country/state/channel/device; store_revenue with store.
"""
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for item in (history or [])[-6:]:
        messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": prompt})
    evidence: list[dict[str, Any]] = []

    for _ in range(4):
        response = client.chat.completions.create(model=model, messages=messages, tools=TOOL_SCHEMAS, tool_choice="auto", temperature=0.2)
        message = response.choices[0].message
        if not message.tool_calls:
            return AgentResponse(message.content or "No response generated.", evidence, f"OpenAI · {model}")
        messages.append(message.model_dump(exclude_none=True))
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")
            try:
                result = dispatch_tool(repo, call.function.name, arguments)
            except Exception as exc:
                result = {"error": str(exc), "tool": call.function.name}
            evidence.append(result)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})

    return AgentResponse("I reached the analysis step limit. Please narrow the question.", evidence, f"OpenAI · {model}")
