# AI Business Analyst Case Study

This file is the single source of truth for the case-study context, working plan, and decision history. Update the relevant section whenever scope, architecture, analytical methodology, model behavior, deployment, or presentation strategy changes.

## 1. Context & workflow instructions

### Purpose

Build an AI Business Analyst for Digital and Retail leaders. The deliverables are a deployed prototype, source code, and a presentation of no more than five slides.

The prototype should help an executive understand performance, quantify business drivers, identify risks and opportunities, receive practical recommendations, and ask follow-up questions.

### Time constraints

- Total exercise: no more than 4 hours
- Prototype, validation, and deployment: target 2 hours 45 minutes; hard limit 3 hours
- Presentation and rehearsal: reserve at least 1 hour
- Reduce scope before adding complexity

### Collaboration rules

- Work step by step so the user controls product and technical decisions.
- Ask before implementing when requirements or tradeoffs are unclear.
- Do not treat a proposed direction as accepted until the user approves it.
- After approval, update this file before moving on.
- Record each material decision as one concise statement that includes the key rationale or tradeoff.
- Keep documentation concise enough to reuse in the final deck.
- Keep exploratory research, validation evidence, visuals, and semantic-contract conclusions in one executed notebook.
- Do not make the application import or execute the notebook; move approved ETL and runtime logic into scripts and modules.
- Prefer DRY and KISS: keep each rule or configuration in one obvious place, avoid provider-specific branches, and do not add hidden fallbacks, hardcoded runtime choices, or manually curated copies of generated analysis.

### Technical and analytical guardrails

- Application: native Streamlit components with no custom CSS or typography; pages are AI Business Analyst, Executive Dashboard, database-derived Data Sources & Schema, and direct rendering of the executed Analysis Notebook
- Data layer: read-only SQLite with four cleaned fact tables (`fact_digital_commerce`, `fact_digital_marketing`, `fact_retail_store`, and restricted `fact_retail_category`), a shared `dim_date`, and SQL metric views
- Preserve source file and source-row metadata in fact tables, keep TY and paired LY measures in separate columns, and use the original workbooks plus ingestion script as the raw record instead of duplicating raw tables in SQLite
- Semantic layer: Python registry for governed metrics, dimensions, filters, formats, and valid grains
- Naming convention: lowercase `<context>_<metric>_<period>` identifiers in SQLite and Python, such as `ga_revenue_ty` and `store_orders_ly`, with title-cased display labels such as `GA Revenue` and `Store Orders`
- Source ownership: Digital commerce for top-line Digital KPIs, Digital marketing for labeled GA diagnostics, Retail store for Retail KPIs, and Retail category blocked pending clarification
- Do not calculate combined Digital + Retail revenue until currency and accounting definitions are confirmed
- Period rules: source coverage is May 3–July 4, 2026 (63 dates spanning three calendar months); support the full available window against supplied LY, use Monday–Sunday complete weeks by default, compare partial weeks only with matched prior-week days, and use calendar months until a shared fiscal calendar is provided
- Agent access: five validated tools (`get_performance_summary`, `analyze_revenue_drivers`, `rank_performance`, `diagnose_stores`, and `forecast_metric`) backed by a safe query builder; never arbitrary LLM-generated SQL
- Response contract: preserve model freedom to choose tools, then require precise metric names, units, exact period references, ranking bases, and percentage-point distinctions within one conclusion-led headline, two or three findings, one action, and one material caveat in 160 words
- Explainability: show the exact period, comparison, and sources above each response; render the final decisive tool result as the primary exhibit; escape currency symbols before Markdown rendering; and keep methods collapsed without raw chain-of-thought or tool JSON
- Keep database access behind a repository interface so a production warehouse can replace SQLite
- Primary deployment: Streamlit Community Cloud; Fly.io is the fallback
- Keep the GitHub repository private unless the supplied data is confirmed safe to publish
- Store secrets in local environment variables or Streamlit Secrets; never commit API keys
- Preprocess the database rather than parsing every workbook on each application cold start
- Do not write conversational or application state to the deployed SQLite database
- Configure the OpenAI-compatible LLM provider, model, base URL, and API key through one explicit runtime configuration; the dashboard remains available without a valid configuration, but the analyst has no deterministic response fallback
- Validate every displayed figure against deterministic calculations
- Preserve legitimate zeros and negative Retail values, label zero-LY cases without calculating infinite growth, remove only confirmed all-zero store placeholders, and display missing dimensions as `Unknown`
- Calculate AOV, conversion, and UPT as ratios of aggregated totals and return no percentage when the denominator is zero
- Surface incomplete coverage and assumptions rather than hiding them

### Definition of done

- The deployed URL works without local setup.
- The primary demo questions return verified answers with evidence.
- Follow-up context works.
- Failure states are presentable.
- No secrets or unintended confidential data are public.
- The five-slide deck covers the problem, experience, architecture, analytical result, recommendations, limitations, and next steps.

## 2. Plan

Use `TODO`, `IN PROGRESS`, `BLOCKED`, and `DONE` tags; check an item only after validating its output.

### Prototype checklist — maximum 2 hours 45 minutes

- [x] **DONE:** Define the executive analyst concept, primary demo journey, technical stack, semantic-layer pattern, and deployment target.
- [x] **DONE — 30 min:** Reviewed and simplified the executed `notebooks/01_data_audit_and_semantic_contract.ipynb` so its analysis, visuals, and conclusions form a clear business story.
- [x] **DONE — 20 min:** Built and validated the one-time Excel-to-SQLite ingestion script with four clean fact tables, a shared date dimension, metric views, lineage fields, and enforced reporting restrictions.
- [x] **DONE — 15 min:** Implemented the Python metric registry, read-only repository, and validated query builder.
- [x] **DONE — 30 min:** Implemented deterministic tools for KPI summaries, period comparisons, revenue drivers, store ranking, and seasonal forecasting.
- [x] **DONE — 30 min:** Built a minimal native Streamlit experience with the AI Business Analyst on page 1 and Executive Dashboard on page 2.
- [x] **DONE — 25 min:** Added provider-independent tool routing, grounded explanations, recommendations, and follow-up context without a hidden response fallback.
- [x] **DONE — 10 min:** Validated metric contracts, read-only access, driver reconciliation, forecasts, invalid-query blocking, Streamlit rendering, and the primary analyst interaction.
- [x] **DONE — 5 min:** Pushed the private `temp-alo-case-study` repository and deployed the public Streamlit Community Cloud app with its LLM secret configured separately.

### Demo acceptance checklist

- [x] **DONE:** Show the latest Digital and Retail KPI summary.
- [x] **DONE:** Answer **“Why did revenue change last week?”** with quantified drivers and evidence.
- [x] **DONE:** Answer **“Which stores need attention, and what should we do?”** with rankings, actions, and limitations.
- [x] **DONE:** Display the period, source, assumptions, and supporting chart or table for each analytical answer.
- [x] **DONE:** Keep the dashboard available without an API key while clearly disabling the AI analyst rather than substituting hidden responses.

### Presentation checklist — reserve at least 1 hour

- [ ] **TODO:** Build no more than five slides covering the problem, experience, architecture, analytical result, recommendations, limitations, and next steps.
- [ ] **TODO:** Reuse the decision log to explain the implementation approach and tradeoffs.
- [ ] **TODO:** Rehearse the deployed demo and prepare a fallback path.

### Scope guardrail

- [x] **DONE:** Exclude unrestricted text-to-SQL, generated Python, complex forecasting, authentication, production infrastructure, exhaustive question support, vector databases, and large agent frameworks.

## 3. Decisions / deck story

### Presentation map

1. Business problem and user
2. Product experience and demo
3. Architecture, AI workflow, and key implementation decisions
4. Business insight and recommendation
5. Assumptions, requested data, and next steps

### Decision log

- **D-001 — Accepted:** Build a focused executive analyst instead of an unrestricted chatbot so the demo emphasizes business reasoning, quantified drivers, and actions.
- **D-002 — Accepted:** Use deterministic Python and governed SQL for every calculation while the LLM selects tools and explains verified results.
- **D-003 — Accepted:** Use Streamlit and Python to protect the three-hour build budget rather than spending time on a custom frontend and API.
- **D-004 — Accepted:** Deploy from a private GitHub repository to Streamlit Community Cloud, with Fly.io as the fallback.
- **D-005 — Reversed:** Keep the dashboard functional without an LLM, but do not present deterministic templates as agent responses when the model is unavailable.
- **D-006 — Accepted:** Limit prototype work to 2 hours 45 minutes and reserve at least one hour for the five-slide deck and rehearsal.
- **D-007 — Accepted:** Use read-only SQLite tables and views plus a Python metric registry to prototype a production-style semantic layer without adding warehouse infrastructure.
- **D-008 — Accepted:** Keep context, plan, and decisions in `AGENTS.md` as the single source of truth to prevent documentation drift.
- **D-009 — Accepted:** Keep every decision-log entry to one concise statement so it remains easy to maintain and reuse in the deck.
- **D-010 — Accepted:** Track the execution plan as a tagged checklist in `AGENTS.md` so progress and remaining work stay visible.
- **D-011 — Accepted:** Use one executed notebook for data research, evidence, visuals, and semantic-contract conclusions, then move approved runtime logic into scripts and modules.
- **D-012 — Accepted:** Write the audit notebook for a business audience, explain technical terms in plain language, and distinguish values needing context from actual data errors.
- **D-013 — Accepted:** Treat Digital tracking and Retail hierarchy issues as testable data-quality hypotheses, not proven causes, and request the metadata needed to validate them.
- **D-014 — Accepted:** Assign Digital top-line metrics to commerce, GA diagnostics to marketing, Retail KPIs to store data, and block category and combined-channel reporting until their definitions reconcile.
- **D-015 — Accepted:** Define weeks as Monday–Sunday, use the latest complete week for full-period reporting, and keep the proposed LY, monthly, and partial-period rules.
- **D-016 — Accepted:** Preserve contextual zeros and possible returns, remove only confirmed placeholders, label unknowns and missing LY baselines honestly, and calculate ratios from aggregated inputs.
- **D-017 — Accepted:** Use four traceable cleaned fact tables, one date dimension, and SQL metric views without duplicating raw tables inside the deployment database.
- **D-018 — Accepted:** Use the approved Digital, GA, and Store metric catalog with context-first lowercase identifiers, friendly display labels, an Orders × AOV Digital bridge, and a Traffic × Conversion × AOV Store bridge.
- **D-019 — Accepted:** Limit the agent to five validated tools for summaries, revenue drivers, rankings, store diagnosis, and simple forecasting while blocking direct database access.
- **D-020 — Accepted:** Use a four-week weekday median for the directional forecast because it remains stable on the short seasonal history and can be explained and holdout-tested clearly.
- **D-021 — Reversed:** Remove the no-key response fallback and require a real model call for every AI analyst answer.
- **D-022 — Accepted:** Use native Streamlit styling without custom CSS or typography to keep the interface minimal.
- **D-023 — Reversed:** Replace direct DeepSeek V4.1 Flash access with a free OpenRouter model.
- **D-024 — Accepted:** Make the AI Business Analyst page 1 and the Executive Dashboard page 2.
- **D-025 — Reversed:** Do not use the free OpenRouter model because interview-demo reliability matters more than avoiding model charges.
- **D-026 — Accepted:** Centralize provider, model, endpoint, and key configuration so switching any OpenAI-compatible tool-calling model requires only configuration changes, with no hidden defaults or fallbacks.
- **D-027 — Accepted:** Configure the deployed app for direct DeepSeek V4.1 Flash access using the generic LLM settings without changing application code.
- **D-028 — Accepted:** Give the model freedom to select analytical tools while enforcing a concise conclusion-led executive response contract.
- **D-029 — Accepted:** Pair each answer with one compact table or chart and an always-visible scope line, then combine tool trace and evidence metadata in one collapsed method section without raw chain-of-thought or JSON.
- **D-030 — Accepted:** Generate the source/schema page from SQLite and the metric registry, and render the existing notebook directly through Streamlit without curated duplicate content or generated files.
- **D-031 — Accepted:** Escape currency symbols before Markdown rendering, require every figure to name its metric, unit, dates, and comparator, and drive the primary exhibit from the final decisive tool result so prose and evidence cannot diverge.
- **D-032 — Accepted:** Describe the dataset as 63 daily dates from May 3 through July 4 spanning three calendar months, and support full-window analysis against supplied LY without implying three complete months or an unavailable prior 63-day window.

### New decision template

- **D-XXX — Proposed | Accepted | Reversed:** Decision and key rationale or tradeoff in one sentence.
