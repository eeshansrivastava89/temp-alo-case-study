from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.agent import run_agent
from src.config import load_llm_config
from src.repository import AnalyticsRepository

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "analytics.db"

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


def configured_llm():
    try:
        secret_values = dict(st.secrets)
    except Exception:
        secret_values = {}
    return load_llm_config(secret_values)


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
    return f"{value:,.0f}"


def sources_for(evidence: list[dict]) -> list[str]:
    sources = []
    for result in evidence:
        context = result.get("context")
        if context in SOURCE_LABELS:
            sources.append(SOURCE_LABELS[context])
        elif result.get("tool") == "diagnose_stores":
            sources.append(SOURCE_LABELS["store"])
        elif result.get("tool") == "forecast_metric":
            metric = result.get("metric", "")
            sources.append(SOURCE_LABELS["ga" if metric.startswith("ga_") else "store" if metric.startswith("store_") else "digital"])
        elif result.get("tool") == "rank_performance":
            metric = result.get("metric", "")
            sources.append(SOURCE_LABELS["ga" if metric.startswith("ga_") else "store" if metric.startswith("store_") else "digital"])
    return list(dict.fromkeys(sources))


def scope_line(evidence: list[dict]) -> str:
    period = next((item.get("period") for item in evidence if item.get("period")), None)
    comparison = next((item.get("comparison") for item in evidence if item.get("comparison")), None)
    pieces = []
    if period:
        pieces.append(f"{period.get('start')} to {period.get('end')}")
    if comparison:
        pieces.append(f"vs. {comparison.get('label')}")
    sources = sources_for(evidence)
    if sources:
        pieces.append("Sources: " + " · ".join(sources))
    return "  |  ".join(pieces)


def render_summary_exhibit(results: list[dict]) -> None:
    rows = []
    for result in results:
        for metric in result.get("metrics", []):
            rows.append(
                {
                    "KPI": metric["label"],
                    "Current": metric_value(metric),
                    "Change": percent(metric["change"]["percent"]),
                }
            )
    if rows:
        st.dataframe(pd.DataFrame(rows[:8]), hide_index=True, width="stretch", height=min(315, 38 + 35 * min(len(rows), 8)))


def render_driver_exhibit(results: list[dict]) -> None:
    rows = []
    for result in results[:2]:
        context = "Digital" if result.get("context") == "digital" else "Stores"
        for factor in result.get("factors", []):
            rows.append(
                {
                    "Driver": f"{context} · {factor['factor']}",
                    "Revenue contribution": factor["revenue_contribution"],
                }
            )
    if rows:
        chart = pd.DataFrame(rows).set_index("Driver")
        st.bar_chart(chart, horizontal=True)
        st.dataframe(
            pd.DataFrame({"Driver": chart.index, "Contribution": [money(value) for value in chart["Revenue contribution"]]}),
            hide_index=True,
            width="stretch",
            height=min(250, 38 + 35 * len(rows)),
        )


def render_rank_exhibit(result: dict) -> None:
    rows = [
        {
            result.get("dimension", "Dimension").title(): item["dimension_value"],
            "Change": item["change"]["absolute"],
            "Change %": percent(item["change"]["percent"]),
        }
        for item in result.get("results", [])[:5]
    ]
    if rows:
        frame = pd.DataFrame(rows)
        st.bar_chart(frame.set_index(frame.columns[0])[["Change"]], horizontal=True)
        display = frame.copy()
        display["Change"] = display["Change"].map(money)
        st.dataframe(display, hide_index=True, width="stretch", height=215)


def render_store_exhibit(result: dict) -> None:
    rows = [
        {
            "Store": str(item["store_id"]),
            "Revenue change": item["revenue_change"]["absolute"],
            "Change %": percent(item["revenue_change"]["percent"]),
            "Driver": item["primary_driver"],
        }
        for item in result.get("stores", [])[:5]
    ]
    if rows:
        frame = pd.DataFrame(rows)
        st.bar_chart(frame.set_index("Store")[["Revenue change"]], horizontal=True)
        display = frame.copy()
        display["Revenue change"] = display["Revenue change"].map(money)
        st.dataframe(display, hide_index=True, width="stretch", height=215)


def render_forecast_exhibit(results: list[dict]) -> None:
    series = []
    for result in results[:2]:
        for point in result.get("daily_forecast", []):
            series.append({"Date": point["date"], "Metric": result["metric_label"], "Forecast": point["value"]})
    if series:
        chart = pd.DataFrame(series).pivot(index="Date", columns="Metric", values="Forecast")
        st.line_chart(chart)
        totals = [
            {"Metric": result["metric_label"], "Forecast": money(result["forecast_total"]), "vs. latest": percent(result["change_vs_recent"]["percent"])}
            for result in results[:2]
        ]
        st.dataframe(pd.DataFrame(totals), hide_index=True, width="stretch", height=110)


def render_primary_exhibit(evidence: list[dict]) -> None:
    by_tool = {}
    for result in evidence:
        by_tool.setdefault(result.get("tool"), []).append(result)

    st.caption("PRIMARY EXHIBIT")
    if by_tool.get("diagnose_stores"):
        render_store_exhibit(by_tool["diagnose_stores"][0])
    elif by_tool.get("rank_performance"):
        render_rank_exhibit(by_tool["rank_performance"][0])
    elif by_tool.get("analyze_revenue_drivers"):
        render_driver_exhibit(by_tool["analyze_revenue_drivers"])
    elif by_tool.get("forecast_metric"):
        render_forecast_exhibit(by_tool["forecast_metric"])
    elif by_tool.get("get_performance_summary"):
        render_summary_exhibit(by_tool["get_performance_summary"])
    else:
        st.caption("No quantitative exhibit was required for this response.")


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
            st.caption(" · ".join(sources_for(evidence)) or "No business source queried")
            methods = list(dict.fromkeys(item.get("method") for item in evidence if item.get("method")))
            for method in methods:
                st.caption(method)


def render_assistant_message(message: dict) -> None:
    evidence = message.get("evidence", [])
    answer, exhibit = st.columns([3, 2])
    with answer:
        st.markdown(message["content"])
    with exhibit:
        render_primary_exhibit(evidence)
    scope = scope_line(evidence)
    if scope:
        st.caption(scope)
    render_method(message)


repo = repository()
llm_config, missing_settings = configured_llm()
model_label = llm_config.display_name if llm_config else "LLM not configured"

st.title("AI Business Analyst")
st.caption(f"Data through {repo.data_through()} · {model_label}")

if missing_settings:
    st.warning(f"Add the required Streamlit Secrets to enable the analyst: {', '.join(missing_settings)}")

with st.expander("Available analysis"):
    st.markdown(
        """
- Digital and Store performance for the latest complete week, latest seven days, or latest complete month
- Revenue drivers, GA channel and device diagnostics, and stores requiring attention
- Directional seven-day forecasts with validation results

Digital commerce is the top-line source. GA metrics remain labeled. Retail category analysis and combined Digital + Store revenue are unavailable because their definitions do not reconcile.
"""
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

suggestions = [
    "How did the business perform last week?",
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
