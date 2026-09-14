"""OpenAI-compatible tool-calling orchestration for the business analyst."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from .config import LLMConfig
from .repository import AnalyticsRepository
from .tools import dispatch_tool


@dataclass
class AgentResponse:
    text: str
    presentation: dict[str, Any]
    evidence: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    model: str


PRESENTATION_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_analysis",
        "description": "Submit the final executive answer and link each finding to one supporting exhibit.",
        "parameters": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "findings": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 3,
                    "items": {
                        "type": "object",
                        "properties": {
                            "statement": {"type": "string"},
                            "exhibit": {
                                "type": "object",
                                "properties": {
                                    "evidence_index": {"type": "integer", "minimum": 0},
                                    "visual": {"type": "string", "enum": ["table", "bar", "line"]},
                                },
                                "required": ["evidence_index", "visual"],
                                "additionalProperties": False,
                            },
                        },
                        "required": ["statement", "exhibit"],
                        "additionalProperties": False,
                    },
                },
                "action": {"type": "string"},
                "watch": {"type": "string"},
            },
            "required": ["headline", "findings", "action"],
            "additionalProperties": False,
        },
    },
}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_performance_summary",
            "description": "Return governed KPIs for Digital commerce, GA diagnostics, or Retail stores. The full available period must use the provided LY comparison.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {"type": "string", "enum": ["digital", "ga", "store"]},
                    "period": {"type": "string", "enum": ["full_available_period", "latest_complete_week", "latest_7_days", "latest_complete_month"]},
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
            "description": "Quantify Digital Orders × AOV or Store Traffic × Conversion × AOV revenue drivers. The full available period must use the provided LY comparison.",
            "parameters": {
                "type": "object",
                "properties": {
                    "context": {"type": "string", "enum": ["digital", "store"]},
                    "period": {"type": "string", "enum": ["full_available_period", "latest_complete_week", "latest_7_days", "latest_complete_month"]},
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
            "description": "Rank an approved geography, GA channel/device, or store dimension by the TY metric level or by metric change. For 'best', rank the TY level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["digital_revenue", "ga_revenue", "ga_sessions", "ga_conversion_rate", "store_revenue"]},
                    "dimension": {"type": "string", "enum": ["country", "state", "channel", "device", "store"]},
                    "period": {"type": "string", "enum": ["full_available_period", "latest_complete_week", "latest_7_days", "latest_complete_month"]},
                    "comparison": {"type": "string", "enum": ["previous_period", "ly"]},
                    "direction": {"type": "string", "enum": ["top", "bottom"]},
                    "ranking_basis": {"type": "string", "enum": ["value", "change"]},
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
    PRESENTATION_TOOL,
]


SUPPORTED_VISUALS = {
    "get_performance_summary": {"table"},
    "analyze_revenue_drivers": {"table", "bar"},
    "rank_performance": {"table", "bar"},
    "diagnose_stores": {"table", "bar"},
    "forecast_metric": {"table", "line"},
}


def _finalize_submission(
    submission: dict[str, Any],
    evidence: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    model: str,
) -> AgentResponse:
    if not submission.get("findings"):
        raise RuntimeError("The model submitted no evidence-linked findings")
    for finding in submission["findings"]:
        exhibit = finding["exhibit"]
        index = exhibit["evidence_index"]
        if index < 0 or index >= len(evidence):
            raise RuntimeError(f"The model referenced unavailable evidence index {index}")
        if evidence[index].get("error"):
            raise RuntimeError(f"The model referenced failed evidence index {index}")
        tool = evidence[index].get("tool")
        if exhibit["visual"] not in SUPPORTED_VISUALS.get(tool, set()):
            raise RuntimeError(f"{exhibit['visual']} is not valid for {tool}")
    text_parts = [submission["headline"]]
    text_parts.extend(f"- {finding['statement']}" for finding in submission["findings"])
    text_parts.append(f"Action: {submission['action']}")
    if submission.get("watch"):
        text_parts.append(f"Watch: {submission['watch']}")
    return AgentResponse("\n".join(text_parts), submission, evidence, steps, model)


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
    inventory = repo.source_inventory()
    available_start = min(item["date_min"] for item in inventory)
    available_end = max(item["date_max"] for item in inventory)
    available_days = (date.fromisoformat(available_end) - date.fromisoformat(available_start)).days + 1
    system = f"""You are an executive business analyst. The complete source window is {available_start} to {available_end} ({available_days} daily dates spanning three calendar months, not three complete months).
Use period=full_available_period and comparison=ly when the user asks for the full dataset, entire period, or all available data; a preceding matched {available_days}-day window is unavailable.
Use the supplied tools for every numerical claim. Never calculate from memory or invent unavailable data.
Digital commerce is the top-line source. GA metrics must remain labeled GA and are diagnostic.
Retail category metrics and combined Digital + Store revenue are blocked.
State the period and comparison, quantify drivers, separate evidence from hypotheses, and recommend validation before consequential action.
Use any relevant analytical tools and preserve analytical freedom. Gather all evidence needed to answer the question rather than optimizing for a single exhibit.
After the analytical calls are complete, call submit_analysis by itself. Write one to three findings; link every finding to the evidence_index that proves it; and choose a table, bar chart, or line chart supported by that result. Use tables for precise multi-metric comparisons, bars for categorical rankings or contributions, and lines for time series. Never cite an exhibit that omits the entity or metric named in its finding.
Final-answer contract: 180 words maximum across the headline, findings, action, and optional watch; use a conclusion-led headline, one to three quantified findings, one action, and a watch only for a material caveat. Do not repeat metrics, expose internal reasoning, overstate causality, or end with a generic offer to do more.
Precision contract:
- Every number must name its metric, unit, exact current period, and comparison reference either in the same sentence or an immediately preceding sentence.
- Use exact governed labels such as Store Revenue, Store Traffic, Store Conversion Rate, Digital Revenue, GA Sessions, and GA Conversion Rate; do not replace them with vague terms such as chain revenue, sales, volume, or performance.
- Write exact dates for both periods. When only supplied LY fields exist, say "supplied LY fields for [requested dates]" and do not invent prior-year dates. Never say only "last week," "week of," "LY," or "prior period."
- Pair monetary amounts with the metric name, for example "$311K of Store Revenue." Never use approximation symbols such as ~ or compact constructions such as "2.3x the decline."
- Distinguish a percentage change from a percentage-point change. For a rate, state the prior rate, current rate, and percentage-point movement.
- When a subset's gross decline exceeds the portfolio's net decline, state the subset decline, portfolio decline, and offset from the remaining entities explicitly.
- Define ranking basis using source terminology. Unless the user specifies otherwise, "best" means highest TY value for the requested dates, not largest growth; use ranking_basis=value. Never use the labels "current value" or "comparator" in prose or exhibit titles.
- For a forecast, define the baseline as the observed total for the exact immediately preceding matched dates, state both date ranges, and clarify that this rolling baseline can differ from the latest complete Monday–Sunday week shown on the dashboard.
- In finding statements only, format every positive signed change as :green[**+value**] and every negative signed change as :red[**−value**] using Streamlit Markdown. Color only directional changes—not unsigned levels, dates, identifiers, or neutral reference values.
- Do not derive a figure that the tools did not return.
Use plain, direct executive language.
Valid ranking pairs: digital_revenue with country/state; ga_revenue, ga_sessions, or ga_conversion_rate with country/state/channel/device; store_revenue with store.
"""
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    messages.extend({"role": item["role"], "content": item["content"]} for item in (history or [])[-6:])
    messages.append({"role": "user", "content": prompt})
    evidence: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []

    for _ in range(6):
        response = client.chat.completions.create(
            model=config.model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
        message = response.choices[0].message
        if not message.tool_calls:
            if not evidence:
                raise RuntimeError("The model attempted to answer without analytical evidence")
            messages.append(message.model_dump(exclude_none=True))
            messages.append(
                {
                    "role": "user",
                    "content": "Submit the answer through submit_analysis now; reference only the evidence_index values returned by the tools.",
                }
            )
            response = client.chat.completions.create(
                model=config.model,
                messages=messages,
                tools=[PRESENTATION_TOOL],
                tool_choice={"type": "function", "function": {"name": "submit_analysis"}},
            )
            message = response.choices[0].message
            if not message.tool_calls:
                raise RuntimeError("The model did not submit a structured analysis")

        submission_calls = [call for call in message.tool_calls if call.function.name == "submit_analysis"]
        if submission_calls:
            if len(message.tool_calls) != 1:
                raise RuntimeError("submit_analysis must be called separately after analytical tools")
            submission_call = submission_calls[0]
            submission = json.loads(submission_call.function.arguments or "{}")
            try:
                return _finalize_submission(submission, evidence, steps, config.display_name)
            except RuntimeError as exc:
                messages.append(message.model_dump(exclude_none=True))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": submission_call.id,
                        "content": json.dumps({"error": str(exc)}),
                    }
                )
                continue

        messages.append(message.model_dump(exclude_none=True))
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")
            steps.append({"tool": call.function.name, "arguments": arguments})
            try:
                result = dispatch_tool(repo, call.function.name, arguments)
            except Exception as exc:
                result = {"tool": call.function.name, "error": str(exc)}
            result["evidence_index"] = len(evidence)
            evidence.append(result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )

    raise RuntimeError("The agent reached its analytical step limit; narrow the question and try again.")
