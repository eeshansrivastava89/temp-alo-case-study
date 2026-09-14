# ALO Performance Intelligence

A Streamlit prototype of an executive AI Business Analyst for Digital commerce, GA diagnostics, and Retail stores.

The application uses governed metrics and deterministic analytical tools for every numerical claim. A configured OpenAI-compatible model selects those tools and explains their results; there is no hidden rule-based response fallback. Answers use precise metric names, units, dates, and comparators alongside the decisive tool's compact exhibit, with methods and exact source files available in one collapsed section.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

LLM configuration is explicit and provider-independent. Example for OpenRouter and NVIDIA Nemotron 3.5 Lightning:

```bash
export LLM_PROVIDER="OpenRouter"
export LLM_MODEL="nvidia/nemotron-3.5-lightning:free"
export LLM_BASE_URL="https://openrouter.ai/api/v1"
export LLM_API_KEY="..."
```

Any OpenAI-compatible tool-calling provider can be selected by changing only these four settings. The app does not choose a default provider or model.

## Demo questions

- How did the business perform last week?
- Why did revenue change last week?
- Which stores need attention, and what should we do?
- What is the seven-day revenue forecast?

## Architecture

```text
Excel → validated ingestion → read-only SQLite metric views
      → governed Python tools → optional LLM orchestration
      → Streamlit executive brief and analyst chat
```

The LLM cannot execute SQL directly. Digital commerce owns top-line Digital metrics, GA remains a labeled diagnostic source, and Retail store data owns Store metrics. Category analysis and combined Digital + Store revenue are blocked because the supplied definitions do not reconcile.

## Project files

- `app.py` — Streamlit page router
- `pages/1_AI_Business_Analyst.py` — page 1: AI Business Analyst
- `pages/2_Executive_Dashboard.py` — page 2: Executive Dashboard
- `pages/3_Data_Sources_and_Schema.py` — page 3: database-derived source catalog, metric model, and schema explorer
- `pages/4_Analysis_Notebook.py` — page 4: direct rendering of the executed notebook
- `src/config.py` — provider-independent LLM configuration contract
- `src/semantic_model.py` — approved metrics and dimensions
- `src/repository.py` — validated read-only queries
- `src/tools.py` — summaries, drivers, rankings, store diagnosis, and forecast
- `src/agent.py` — OpenRouter tool routing
- `scripts/build_database.py` — reproducible Excel-to-SQLite ingestion
- `notebooks/01_data_audit_and_semantic_contract.ipynb` — executed audit, visuals, assumptions, and contract
- `AGENTS.md` — plan and decision history

## Validate

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Known limitations

The prototype does not have marketing spend, inventory, promotions, pricing, product costs, an official fiscal calendar, category hierarchy metadata, or GA implementation history. Forecasts are directional seasonal baselines rather than planning forecasts.
