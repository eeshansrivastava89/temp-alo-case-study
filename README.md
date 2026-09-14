# ALO Performance Intelligence

A Streamlit prototype of an executive AI Business Analyst for Digital commerce, GA diagnostics, and Retail stores.

The application uses governed metrics and deterministic analytical tools for every numerical claim. A configured OpenAI-compatible model selects those tools and links each executive finding to validated evidence, choosing a supported table, bar chart, or line chart. Responses use precise metric names, TY/LY or exact-date references, and native color coding for signed changes; there is no hidden analytical fallback.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

LLM configuration is explicit and provider-independent. Example for Ollama Cloud and GLM-5.3:

```bash
export LLM_PROVIDER="Ollama Cloud"
export LLM_MODEL="glm-5.3:cloud"
export LLM_BASE_URL="https://ollama.com/v1/"
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
- `src/agent.py` — provider-independent tool routing and structured presentation contract
- `scripts/build_database.py` — reproducible Excel-to-SQLite ingestion
- `notebooks/01_data_audit_and_semantic_contract.ipynb` — executed audit, visuals, assumptions, and contract

## Validate

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Known limitations

The available source window contains 63 daily dates from May 3 through July 4, 2026, spanning three calendar months rather than three complete months; full-window comparisons use the supplied LY fields. The prototype does not have marketing spend, inventory, promotions, pricing, product costs, an official fiscal calendar, category hierarchy metadata, or GA implementation history. Forecasts are directional seasonal baselines rather than planning forecasts.
