from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import re

import pandas as pd
import streamlit as st

from src.agent import run_agent
from src.config import load_llm_config
from src.repository import AnalyticsRepository
from src.semantic_model import CONTEXT_VIEWS

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "analytics.db"
MESSAGE_SCHEMA_VERSION = 3

TOOL_LABELS = {
    "get_performance_summary": "Performance summary",
    "analyze_revenue_drivers": "Revenue drivers",
    "rank_performance": "Performance ranking",
    "diagnose_stores": "Store diagnosis",
    "forecast_metric": "Forecast",
}

SOURCE_LABELS = {
    "digital": "Digital commerce",
    "ga": "GA diagnostics",
    "store": "Retail store",
}


@st.cache_resource
def repository() -> AnalyticsRepository:
    return AnalyticsRepository(DB_PATH)


@st.cache_data
def source_inventory() -> list[dict]:
    return repository().source_inventory()


def configured_llm():
    try:
        secret_values = dict(st.secrets)
    except Exception:
        secret_values = {}
    return load_llm_config(secret_values)


def markdown_text(value: str) -> str:
    """Prevent currency amounts from being parsed as inline LaTeX by Streamlit."""
    return re.sub(r"(?<!\\)\$(?=\s?\d)", r"\\$", value)


def color_signed_changes(value: str) -> str:
    """Apply native Streamlit colors to signed changes while preserving model-applied colors."""
    protected: list[str] = []

    def protect(match: re.Match) -> str:
        protected.append(match.group(0))
        return f"@@COLOR{len(protected) - 1}@@"

    value = re.sub(r":(?:green|red)\[\*\*.*?\*\*\]", protect, value)
    pattern = r"(?<![\w])([+−-]\s?\$?\d[\d,]*(?:\.\d+)?\s?(?:[KMB]|%|pp)?)(?![\w-])"

    def color(match: re.Match) -> str:
        change = match.group(1)
        color_name = "green" if change.lstrip().startswith("+") else "red"
        return f":{color_name}[**{change}**]"

    value = re.sub(pattern, color, value, flags=re.IGNORECASE)
    for index, colored in enumerate(protected):
        value = value.replace(f"@@COLOR{index}@@", colored)
    return value


def money(value: float | None) -> str:
    if value is None:
        return "n/a"
    sign = "−" if value < 0 else ""
    magnitude = abs(value)
    if magnitude >= 1_000_000:
        return f"{sign}${magnitude / 1_000_000:.2f}M"
    if magnitude >= 1_000:
        return f"{sign}${magnitude / 1_000:.0f}K"
    return f"{sign}${magnitude:,.0f}"


def percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.1%}".replace("-", "−")


def metric_value(metric: dict) -> str:
    value = metric.get("value")
    if value is None:
        return "n/a"
    if metric.get("format") == "currency":
        return money(value)
    if metric.get("format") == "percent":
        return f"{value:.1%}"
    if metric.get("format") == "decimal":
        return f"{value:,.2f}"
    return f"{value:,.0f}"


def contexts_for(evidence: list[dict]) -> list[str]:
    contexts = []
    for result in evidence:
        context = result.get("context")
        if context in SOURCE_LABELS:
            contexts.append(context)
        elif result.get("tool") == "diagnose_stores":
            contexts.append("store")
        elif result.get("tool") in {"forecast_metric", "rank_performance"}:
            metric = result.get("metric", "")
            contexts.append("ga" if metric.startswith("ga_") else "store" if metric.startswith("store_") else "digital")
    return list(dict.fromkeys(contexts))


def sources_for(evidence: list[dict]) -> list[str]:
    return [SOURCE_LABELS[context] for context in contexts_for(evidence)]


def source_files_for(evidence: list[dict]) -> list[str]:
    by_view = {item["metric_view"]: item for item in source_inventory()}
    files = []
    for context in contexts_for(evidence):
        source = by_view.get(CONTEXT_VIEWS[context])
        if source:
            files.append(f"{source['source_file']} · {source['sheet']}")
    return files


def forecast_baseline_period(forecast: dict) -> dict:
    if forecast.get("baseline_period"):
        return forecast["baseline_period"]
    days = len(forecast["daily_forecast"])
    baseline_end = date.fromisoformat(forecast["forecast_period"]["start"]) - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=days - 1)
    return {"start": baseline_start.isoformat(), "end": baseline_end.isoformat(), "days": days}


def scope_line(evidence: list[dict]) -> str:
    period = next((item.get("period") for item in evidence if item.get("period")), None)
    comparison = next((item.get("comparison") for item in evidence if item.get("comparison")), None)
    forecast_result = next((item for item in evidence if item.get("forecast_period")), None)
    forecast_period = forecast_result.get("forecast_period") if forecast_result else None
    baseline_period = forecast_baseline_period(forecast_result) if forecast_result else None
    pieces = []
    if forecast_period:
        pieces.append(f"Forecast: {forecast_period.get('start')} to {forecast_period.get('end')}")
    elif period:
        pieces.append(f"{period.get('start')} to {period.get('end')}")
    if baseline_period:
        pieces.append(f"vs. observed: {baseline_period.get('start')} to {baseline_period.get('end')}")
    elif comparison:
        pieces.append(f"vs. {comparison.get('label')}")
    sources = sources_for(evidence)
    if sources:
        pieces.append("Sources: " + " · ".join(sources))
    return "  |  ".join(pieces)


def comparison_headers(result: dict, metric_label: str | None = None) -> tuple[str, str, str]:
    comparison = result.get("comparison", {})
    period = result.get("period", {})
    if comparison.get("type") == "ly":
        prefix = f"{metric_label} " if metric_label else ""
        return f"{prefix}TY", f"{prefix}LY", "TY vs LY"
    prefix = f"{metric_label} · " if metric_label else ""
    return (
        f"{prefix}{period.get('start')} to {period.get('end')}",
        f"{prefix}{comparison.get('label')}",
        "Period change",
    )


def formatted_change(metric: dict) -> str:
    if metric.get("format") == "percent":
        movement = metric.get("change", {}).get("absolute")
        return "n/a" if movement is None else f"{movement * 100:+.2f} pp".replace("-", "−")
    return percent(metric.get("change", {}).get("percent"))


def render_summary_exhibit(result: dict) -> None:
    ty_header, baseline_header, change_header = comparison_headers(result)
    rows = []
    for metric in result.get("metrics", []):
        rows.append(
            {
                "KPI": metric["label"],
                ty_header: metric_value(metric),
                baseline_header: metric_value({**metric, "value": metric.get("baseline")}),
                change_header: formatted_change(metric),
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=min(315, 38 + 35 * len(rows)))


def render_driver_exhibit(result: dict, visual: str) -> None:
    metric_label = "Digital Revenue" if result.get("context") == "digital" else "Store Revenue"
    value_header = f"{metric_label} contribution"
    rows = [{"Driver": item["factor"], value_header: item["revenue_contribution"]} for item in result.get("factors", [])]
    frame = pd.DataFrame(rows)
    if visual == "bar":
        st.bar_chart(frame, x="Driver", y=value_header, horizontal=True, sort=False)
    else:
        display = frame.copy()
        display[value_header] = display[value_header].map(money)
        st.dataframe(display, hide_index=True, width="stretch")


def render_store_profile_exhibit(result: dict) -> bool:
    if result.get("dimension") != "store" or result.get("ranking_basis") != "value" or not result.get("results"):
        return False
    leader = result["results"][0]
    if not leader.get("profile"):
        return False
    ty_header, baseline_header, change_header = comparison_headers(result)
    rows = [
        {
            "KPI": metric["label"],
            ty_header: metric_value(metric),
            baseline_header: metric_value({**metric, "value": metric.get("baseline")}),
            change_header: formatted_change(metric),
        }
        for metric in leader["profile"]
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=283)
    st.caption(
        f"Store {leader['dimension_value']} ranks first among {result.get('entities_evaluated', 'all')} stores by Store Revenue TY for the requested dates."
    )
    return True


def rank_value(metric_format: str, value: float | None) -> str:
    if value is None:
        return "n/a"
    if metric_format == "currency":
        return money(value)
    if metric_format == "percent":
        return f"{value:.2%}"
    return f"{value:,.0f}"


def render_rank_exhibit(result: dict, visual: str) -> None:
    if visual == "table" and render_store_profile_exhibit(result):
        return
    metric_label = result["metric_label"]
    dimension_header = result.get("dimension", "Dimension").title()
    ty_header, baseline_header, change_header = comparison_headers(result, metric_label)
    items = result.get("results", [])[:8]
    rows = [
        {
            dimension_header: item["dimension_value"],
            ty_header: item["value"],
            baseline_header: item["baseline"],
            change_header: item["change"]["percent"],
        }
        for item in items
    ]
    frame = pd.DataFrame(rows)
    if visual == "bar":
        if result.get("ranking_basis") == "change":
            change_value_header = f"{metric_label} absolute change"
            chart = pd.DataFrame(
                {
                    dimension_header: [item["dimension_value"] for item in items],
                    change_value_header: [item["change"]["absolute"] for item in items],
                }
            )
            st.bar_chart(chart, x=dimension_header, y=change_value_header, horizontal=True, sort=False)
        else:
            chart = frame[[dimension_header, ty_header, baseline_header]].copy()
            if result.get("metric_format") == "percent":
                chart[ty_header] *= 100
                chart[baseline_header] *= 100
                chart = chart.rename(columns={ty_header: f"{ty_header} (%)", baseline_header: f"{baseline_header} (%)"})
                ty_header, baseline_header = f"{ty_header} (%)", f"{baseline_header} (%)"
            st.bar_chart(chart, x=dimension_header, y=[ty_header, baseline_header], horizontal=True, sort=False)
    else:
        display = frame.copy()
        display[ty_header] = display[ty_header].map(lambda value: rank_value(result.get("metric_format", "integer"), value))
        display[baseline_header] = display[baseline_header].map(lambda value: rank_value(result.get("metric_format", "integer"), value))
        display[change_header] = display[change_header].map(percent)
        st.dataframe(display, hide_index=True, width="stretch", height=min(320, 38 + 35 * len(display)))
    if len(result.get("results", [])) > len(items):
        st.caption(f"Showing {len(items)} of {len(result['results'])} returned {result.get('dimension', 'dimension')} records.")


def render_store_exhibit(result: dict, visual: str) -> None:
    rows = [
        {
            "Store": str(item["store_id"]),
            "Store Revenue change": item["revenue_change"]["absolute"],
            "Store Revenue change %": item["revenue_change"]["percent"],
            "Primary driver": item["primary_driver"],
        }
        for item in result.get("stores", [])[:8]
    ]
    frame = pd.DataFrame(rows)
    if visual == "bar":
        st.bar_chart(frame, x="Store", y="Store Revenue change", horizontal=True, sort=False)
    else:
        display = frame.copy()
        display["Store Revenue change"] = display["Store Revenue change"].map(money)
        display["Store Revenue change %"] = display["Store Revenue change %"].map(percent)
        st.dataframe(display, hide_index=True, width="stretch", height=min(320, 38 + 35 * len(display)))


def render_forecast_exhibit(result: dict, visual: str) -> None:
    forecast = result["forecast_period"]
    baseline = forecast_baseline_period(result)
    if visual == "line":
        series = pd.DataFrame(result.get("daily_forecast", [])).rename(columns={"date": "Date", "value": result["metric_label"]})
        st.line_chart(series, x="Date", y=result["metric_label"])
    else:
        rows = [
            {
                "Measure": f"Observed · {baseline['start']} to {baseline['end']}",
                result["metric_label"]: money(result["recent_baseline_total"]),
                "Forecast vs observed": "—",
            },
            {
                "Measure": f"Forecast · {forecast['start']} to {forecast['end']}",
                result["metric_label"]: money(result["forecast_total"]),
                "Forecast vs observed": percent(result["change_vs_recent"]["percent"]),
            },
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=145)


def exhibit_title(result: dict) -> str:
    tool = result.get("tool")
    if tool == "rank_performance":
        ty_header, baseline_header, _ = comparison_headers(result, result["metric_label"])
        return f"{ty_header} vs {baseline_header} by {result['dimension'].title()}"
    if tool == "analyze_revenue_drivers":
        metric = "Digital Revenue" if result.get("context") == "digital" else "Store Revenue"
        return f"{metric} change decomposition"
    if tool == "diagnose_stores":
        return "Store Revenue declines by Store"
    if tool == "forecast_metric":
        return f"{result['metric_label']} observed baseline and forecast"
    ty_header, baseline_header, _ = comparison_headers(result)
    return f"{result.get('context_label', 'KPI')} KPIs · {ty_header} vs {baseline_header}"


def render_evidence(result: dict, visual: str) -> None:
    st.caption(exhibit_title(result).upper())
    tool = result.get("tool")
    if tool == "get_performance_summary":
        render_summary_exhibit(result)
    elif tool == "analyze_revenue_drivers":
        render_driver_exhibit(result, visual)
    elif tool == "rank_performance":
        render_rank_exhibit(result, visual)
    elif tool == "diagnose_stores":
        render_store_exhibit(result, visual)
    elif tool == "forecast_metric":
        render_forecast_exhibit(result, visual)


def render_method(message: dict) -> None:
    steps = message.get("steps", [])
    evidence = message.get("evidence", [])
    with st.expander("Method & sources"):
        left, right = st.columns(2)
        with left:
            st.markdown("**Tools used**")
            if steps:
                for index, step in enumerate(steps, start=1):
                    arguments = ", ".join(f"{key}={value}" for key, value in step.get("arguments", {}).items())
                    st.caption(f"{index}. {TOOL_LABELS.get(step['tool'], step['tool'])}" + (f" · {arguments}" if arguments else ""))
            else:
                st.caption("No analytical tool was required.")
        with right:
            st.markdown("**Model and data**")
            st.caption(message.get("model", "Model unavailable"))
            source_files = source_files_for(evidence)
            if source_files:
                for source in source_files:
                    st.caption(source)
            else:
                st.caption("No business source queried")
            methods = list(dict.fromkeys(item.get("method") for item in evidence if item.get("method")))
            for method in methods:
                st.caption(method)


def render_assistant_message(message: dict) -> None:
    evidence = message.get("evidence", [])
    presentation = message.get("presentation")
    scope = scope_line(evidence)
    if scope:
        st.caption(scope)
    if not presentation:
        st.markdown(markdown_text(message["content"]))
        render_method(message)
        return

    st.markdown(f"**{markdown_text(presentation['headline'])}**")
    for finding in presentation["findings"]:
        statement = markdown_text(color_signed_changes(finding["statement"]))
        st.markdown(f"- {statement}")
        exhibit = finding["exhibit"]
        render_evidence(evidence[exhibit["evidence_index"]], exhibit["visual"])
    st.markdown(f"**Action:** {markdown_text(presentation['action'])}")
    if presentation.get("watch"):
        st.markdown(f"**Watch:** {markdown_text(presentation['watch'])}")
    render_method(message)


repo = repository()
inventory = source_inventory()
available_start = min(item["date_min"] for item in inventory)
available_end = max(item["date_max"] for item in inventory)
available_days = (pd.Timestamp(available_end) - pd.Timestamp(available_start)).days + 1
llm_config, missing_settings = configured_llm()
model_label = llm_config.display_name if llm_config else "LLM not configured"

st.title("AI Business Analyst")
st.caption(f"Data available {available_start} to {available_end} · {available_days} days · {model_label}")

if missing_settings:
    st.warning(f"Add the required Streamlit Secrets to enable the analyst: {', '.join(missing_settings)}")

with st.expander("Available analysis"):
    st.markdown(
        """
- Source coverage: May 3–July 4, 2026—63 daily dates spanning three calendar months, not three complete months
- Digital and Store performance for the full available window, latest complete month, latest complete week, or latest seven days
- Revenue drivers, GA channel and device diagnostics, and stores requiring attention
- Directional seven-day forecasts with validation results

The full-window comparison uses the supplied LY fields because an earlier matched 63-day period is not included. Digital commerce is the top-line source. GA metrics remain labeled. Retail category analysis and combined Digital + Store revenue are unavailable because their definitions do not reconcile.
"""
    )

if st.session_state.get("message_schema_version") != MESSAGE_SCHEMA_VERSION:
    st.session_state.messages = []
    st.session_state.message_schema_version = MESSAGE_SCHEMA_VERSION

suggestions = [
    "How did the business perform across the full available period?",
    "Why did revenue change last week?",
    "Which stores need attention, and what should we do?",
    "What is the seven-day revenue forecast?",
]

suggested_prompt = None
columns = st.columns(2)
for index, suggestion in enumerate(suggestions):
    if columns[index % 2].button(suggestion, width="stretch", disabled=llm_config is None):
        suggested_prompt = suggestion

st.divider()
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and message.get("evidence") is not None:
            render_assistant_message(message)
        else:
            st.markdown(message["content"])

entered_prompt = st.chat_input("Ask about performance, drivers, stores, channels, or risk", disabled=llm_config is None)
prompt = suggested_prompt or entered_prompt

if prompt:
    if llm_config is None:
        st.error("The LLM configuration is incomplete.")
        st.stop()
    history = [{"role": item["role"], "content": item["content"]} for item in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Analyzing…"):
                response = run_agent(repo, prompt, history, config=llm_config)
            assistant_message = {
                "role": "assistant",
                "content": response.text,
                "presentation": response.presentation,
                "evidence": response.evidence,
                "steps": response.steps,
                "model": response.model,
            }
            render_assistant_message(assistant_message)
            st.session_state.messages.append(assistant_message)
        except Exception as exc:
            error_message = f"The analyst could not complete this request: {exc}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
