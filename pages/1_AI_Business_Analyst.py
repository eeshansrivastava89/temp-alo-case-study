from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.agent import run_agent
from src.config import load_llm_config
from src.repository import AnalyticsRepository

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "analytics.db"


@st.cache_resource
def repository() -> AnalyticsRepository:
    return AnalyticsRepository(DB_PATH)


def configured_llm():
    try:
        secret_values = dict(st.secrets)
    except Exception:
        secret_values = {}
    return load_llm_config(secret_values)


repo = repository()
llm_config, missing_settings = configured_llm()
model_label = llm_config.display_name if llm_config else "LLM not configured"

st.title("AI Business Analyst")
st.caption(f"Data through {repo.data_through()} · {model_label} · governed analytics tools")

if missing_settings:
    st.warning(f"Add the required Streamlit Secrets to enable the analyst: {', '.join(missing_settings)}")

with st.expander("What the analyst can answer"):
    st.markdown(
        """
- Digital and Store performance for the latest complete week, latest seven days, or latest complete month
- Revenue drivers, GA channel and device diagnostics, and stores requiring attention
- Directional seven-day forecasts with validation results

Digital commerce is the top-line source. GA metrics remain clearly labeled. Retail category analysis and combined Digital + Store revenue are unavailable because their definitions do not reconcile.
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

st.subheader("Suggested questions")
suggested_prompt = None
columns = st.columns(2)
for index, suggestion in enumerate(suggestions):
    if columns[index % 2].button(suggestion, width="stretch", disabled=llm_config is None):
        suggested_prompt = suggestion

st.divider()
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("evidence"):
            with st.expander("Evidence used"):
                st.json(message["evidence"])

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
                response = run_agent(
                    repo,
                    prompt,
                    history,
                    config=llm_config,
                )
            st.markdown(response.text)
            st.caption(f"Model: {response.model}")
            if response.evidence:
                with st.expander("Evidence used"):
                    st.json(response.evidence)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "evidence": response.evidence,
                }
            )
        except Exception as exc:
            message = f"The analyst could not complete this request: {exc}"
            st.error(message)
            st.session_state.messages.append({"role": "assistant", "content": message})
