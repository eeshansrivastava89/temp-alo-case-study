from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.agent import run_agent
from src.repository import AnalyticsRepository
from src.tools import analyze_revenue_drivers, diagnose_stores, forecast_metric, get_performance_summary

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "analytics.db"

st.set_page_config(page_title="ALO Performance Intelligence", page_icon="◼", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap');
:root { --ink:#171a18; --forest:#1f5c4a; --paper:#f4f1e9; --line:rgba(23,26,24,.14); }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:var(--ink); }
h1, h2, h3 { font-family:'Newsreader',serif !important; font-weight:500 !important; letter-spacing:-.025em; }
.block-container { max-width:1240px; padding-top:2.2rem; padding-bottom:4rem; }
[data-testid="stMetric"] { background:rgba(255,255,255,.48); border:1px solid var(--line); padding:1.05rem 1.1rem; border-radius:3px; }
[data-testid="stMetricLabel"] { text-transform:uppercase; letter-spacing:.09em; font-size:.69rem; }
[data-testid="stMetricValue"] { font-family:'Newsreader',serif; letter-spacing:-.03em; }
[data-testid="stMetricDelta"] { font-size:.78rem; }
.stTabs [data-baseweb="tab-list"] { gap:1.7rem; border-bottom:1px solid var(--line); }
.stTabs [data-baseweb="tab"] { padding:0 0 .8rem; background:transparent; text-transform:uppercase; letter-spacing:.08em; font-size:.72rem; }
.stTabs [aria-selected="true"] { color:var(--forest) !important; border-bottom:2px solid var(--forest); }
.stButton > button { border:1px solid var(--line); border-radius:999px; background:rgba(255,255,255,.42); }
.stButton > button:hover { border-color:var(--forest); color:var(--forest); }
[data-testid="stChatMessage"] { background:rgba(255,255,255,.4); border:1px solid var(--line); border-radius:4px; padding:.65rem 1rem; }
.eyebrow { text-transform:uppercase; letter-spacing:.17em; font-size:.68rem; font-weight:600; color:var(--forest); }
.hero { display:flex; justify-content:space-between; align-items:end; border-bottom:1px solid var(--line); padding-bottom:1.4rem; margin-bottom:1rem; }
.hero h1 { font-size:clamp(2.4rem,5vw,4.6rem); line-height:.92; margin:.4rem 0 0; }
.hero-meta { text-align:right; font-size:.75rem; line-height:1.7; color:#5a5f5b; }
.signal { border-left:3px solid var(--forest); padding:.2rem 0 .2rem 1rem; margin:.8rem 0 1.2rem; }
.signal strong { font-family:'Newsreader',serif; font-size:1.35rem; font-weight:500; }
.note { color:#676d68; font-size:.8rem; }
.mode { display:inline-block; padding:.25rem .55rem; border:1px solid var(--line); border-radius:999px; font-size:.67rem; letter-spacing:.08em; text-transform:uppercase; }
hr { border-color:var(--line); }
</style>
""",
    unsafe_allow_html=True,
)


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


def delta(metric: dict) -> str:
    change = metric["change"]["percent"]
    return "No baseline" if change is None else f"{change:+.1%} vs prior week"


def render_metrics(summary: dict) -> None:
    columns = st.columns(len(summary["metrics"]))
    for column, metric in zip(columns, summary["metrics"], strict=True):
        column.metric(metric["label"], display_value(metric), delta(metric))


def driver_frame(result: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Driver": item["factor"], "Revenue contribution": item["revenue_contribution"]} for item in result["factors"]]
    ).set_index("Driver")


repo = repository()
data = dashboard_data()
period = data["digital"]["period"]
api_key = os.getenv("OPENAI_API_KEY")
try:
    api_key = st.secrets.get("OPENAI_API_KEY", api_key)
    model = st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")
except Exception:
    model = "gpt-4o-mini"

st.markdown(
    f"""
<div class="hero">
  <div><div class="eyebrow">ALO · Performance intelligence</div><h1>Executive pulse</h1></div>
  <div class="hero-meta">DATA THROUGH {repo.data_through()}<br>LAST COMPLETE WEEK · {period['start']} → {period['end']}<br><span class="mode">{'Live AI' if api_key else 'Deterministic demo'}</span></div>
</div>
""",
    unsafe_allow_html=True,
)

overview_tab, analyst_tab, trust_tab = st.tabs(["Executive brief", "Ask the analyst", "Data trust"])

with overview_tab:
    st.markdown("### Digital commerce")
    render_metrics(data["digital"])
    st.caption("Top-line commerce source · previous complete Monday–Sunday week comparison")

    st.markdown("### Retail stores")
    render_metrics(data["store"])
    st.caption("Store Revenue maps to supplied net sales · previous complete Monday–Sunday week comparison")

    st.divider()
    left, right = st.columns([1, 1], gap="large")
    with left:
        digital_change = data["digital_drivers"]["revenue"]["change"]
        st.markdown("#### What moved revenue")
        st.markdown(
            f"<div class='signal'><strong>Digital Revenue {money(digital_change['absolute'])}</strong><br><span class='note'>Orders pressure was partly offset by AOV.</span></div>",
            unsafe_allow_html=True,
        )
        st.bar_chart(driver_frame(data["digital_drivers"]), horizontal=True, color="#1f5c4a")
        ga_metrics = {item["metric"]: item for item in data["digital_drivers"]["supporting_ga_diagnostics"]}
        st.caption(
            f"GA context: sessions {ga_metrics['ga_sessions']['change']['percent']:+.1%}; "
            f"tracked conversion {ga_metrics['ga_conversion_rate']['change']['percent']:+.1%}. "
            "Traffic quality and tracking are hypotheses to validate."
        )

    with right:
        store_change = data["store_drivers"]["revenue"]["change"]
        st.markdown("#### Store operating bridge")
        st.markdown(
            f"<div class='signal'><strong>Store Revenue {money(store_change['absolute'])}</strong><br><span class='note'>Conversion was the primary drag; AOV and traffic cushioned it.</span></div>",
            unsafe_allow_html=True,
        )
        st.bar_chart(driver_frame(data["store_drivers"]), horizontal=True, color="#9a5a3a")
        st.caption("Shapley contributions reconcile exactly to the period-over-period revenue change.")

    st.divider()
    st.markdown("### Stores requiring attention")
    store_rows = []
    for item in data["stores"]["stores"]:
        store_rows.append(
            {
                "Store": str(item["store_id"]),
                "Revenue change": money(item["revenue_change"]["absolute"]),
                "Change %": f"{item['revenue_change']['percent']:+.1%}",
                "Primary driver": item["primary_driver"],
                "Recommended check": item["recommended_check"],
            }
        )
    st.dataframe(pd.DataFrame(store_rows), hide_index=True, width="stretch")

    forecast_left, forecast_right = st.columns(2)
    for column, forecast in [(forecast_left, data["digital_forecast"]), (forecast_right, data["store_forecast"])]:
        with column:
            st.markdown(f"#### {forecast['metric_label']} · next 7 days")
            st.metric(
                forecast["metric_label"],
                money(forecast["forecast_total"]),
                f"{forecast['change_vs_recent']['percent']:+.1%} vs latest 7 days",
            )
            st.caption(f"Seasonal weekday baseline · holdout MAPE {forecast['validation']['mape']:.1%}")

with analyst_tab:
    st.markdown("## Ask a business question")
    st.caption("Every numerical claim comes from a governed tool. Follow-up questions retain recent conversation context.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    suggestions = [
        "How did the business perform last week?",
        "Why did revenue change last week?",
        "Which stores need attention, and what should we do?",
        "What is the seven-day revenue forecast?",
    ]
    suggested_prompt = None
    suggestion_columns = st.columns(2)
    for index, suggestion in enumerate(suggestions):
        if suggestion_columns[index % 2].button(suggestion, width="stretch"):
            suggested_prompt = suggestion

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("evidence"):
                with st.expander("Evidence used"):
                    st.json(message["evidence"])

    typed_prompt = st.chat_input("Ask about performance, drivers, stores, channels, or risk")
    prompt = suggested_prompt or typed_prompt
    if prompt:
        prior_history = [{"role": item["role"], "content": item["content"]} for item in st.session_state.messages]
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Running governed analysis…"):
                response = run_agent(repo, prompt, prior_history, api_key=api_key, model=model)
            st.markdown(response.text)
            st.caption(response.mode)
            if response.evidence:
                with st.expander("Evidence used"):
                    st.json(response.evidence)
        st.session_state.messages.append(
            {"role": "assistant", "content": response.text, "evidence": response.evidence, "mode": response.mode}
        )

with trust_tab:
    st.markdown("## Data trust before confident answers")
    st.markdown(
        """
| Question | Approved source | Guardrail |
|---|---|---|
| Digital topline | Digital commerce | Unknown geography stays in totals but not state claims |
| Channel and device | GA diagnostics | Always labeled GA; not forced to match commerce |
| Store performance | Retail store | Negative values retained as possible returns |
| Product category | Restricted | Totals do not reconcile to store revenue |
| Combined business revenue | Restricted | Currency and gross/net definitions are missing |
"""
    )
    st.markdown("### Known questions for the business")
    st.markdown(
        """
- Did GA ecommerce tagging, consent behavior, or market coverage change?
- Is the category file mixing hierarchy levels, rollups, or a different transformation?
- What is the shared fiscal calendar and reporting currency?
- Which promotions, inventory constraints, store hours, and marketing investments affected the period?
"""
    )
    st.info("Recommendations are decision prompts, not causal claims. Validate operational hypotheses with source owners before acting.")
