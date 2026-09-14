# ALO Performance Intelligence

A Streamlit prototype of an executive AI Business Analyst for Digital commerce, GA diagnostics, and Retail stores.

The application uses governed metrics and deterministic analytical tools for every numerical claim. An optional OpenAI layer selects tools and explains their results; without an API key, the same demo questions use deterministic responses.

## Run locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Optional live AI configuration:

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4o-mini"
```

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

- `app.py` — Streamlit interface
- `src/semantic_model.py` — approved metrics and dimensions
- `src/repository.py` — validated read-only queries
- `src/tools.py` — summaries, drivers, rankings, store diagnosis, and forecast
- `src/agent.py` — LLM tool routing and deterministic fallback
- `scripts/build_database.py` — reproducible Excel-to-SQLite ingestion
- `notebooks/01_data_audit_and_semantic_contract.ipynb` — executed audit, visuals, assumptions, and contract
- `AGENTS.md` — plan and decision history

## Validate

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Known limitations

The prototype does not have marketing spend, inventory, promotions, pricing, product costs, an official fiscal calendar, category hierarchy metadata, or GA implementation history. Forecasts are directional seasonal baselines rather than planning forecasts.
