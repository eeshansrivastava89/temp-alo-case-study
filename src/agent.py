"""OpenRouter tool-calling orchestration for the business analyst."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .config import LLMConfig
from .repository import AnalyticsRepository
from .tools import dispatch_tool


@dataclass
class AgentResponse:
    text: str
    evidence: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    model: str


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


def run_agent(
    repo: AnalyticsRepository,
    prompt: str,
    history: list[dict[str, str]] | None = None,
    *,
    config: LLMConfig,
) -> AgentResponse:
    from openai import OpenAI

    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=120,
    )
    system = f"""You are an executive business analyst. Data is available through {repo.data_through()}.
Use the supplied tools for every numerical claim. Never calculate from memory or invent unavailable data.
Digital commerce is the top-line source. GA metrics must remain labeled GA and are diagnostic.
Retail category metrics and combined Digital + Store revenue are blocked.
State the period and comparison, quantify drivers, separate evidence from hypotheses, and recommend validation before consequential action.
Use any relevant tools and preserve analytical freedom, but prefer the smallest sufficient set.
The interface renders tables and charts, so do not create a table in the written response.
Final-answer contract: 160 words maximum; start with one bold conclusion-led headline; give two or three quantified bullets; add one bold Action line; add one brief Watch line only when a material caveat exists. Do not repeat metrics, add multiple sections, expose internal reasoning, overstate causality, or end with a generic offer to do more.
Use plain executive language and format currency and percentages cleanly.
Valid ranking pairs: digital_revenue with country/state; ga_revenue, ga_sessions, or ga_conversion_rate with country/state/channel/device; store_revenue with store.
"""
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    messages.extend({"role": item["role"], "content": item["content"]} for item in (history or [])[-6:])
    messages.append({"role": "user", "content": prompt})
    evidence: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []

    for _ in range(4):
        response = client.chat.completions.create(
            model=config.model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        message = response.choices[0].message
        if not message.tool_calls:
            return AgentResponse(message.content or "No response generated.", evidence, steps, config.display_name)

        messages.append(message.model_dump(exclude_none=True))
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")
            steps.append({"tool": call.function.name, "arguments": arguments})
            try:
                result = dispatch_tool(repo, call.function.name, arguments)
            except Exception as exc:
                result = {"tool": call.function.name, "error": str(exc)}
            evidence.append(result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )

    raise RuntimeError("The agent reached its four-step tool limit; narrow the question and try again.")
