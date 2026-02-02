# Dashboard

A three-page Streamlit app: revenue overview, category trends, fulfilment timing. See the main [README](../README.md#what-the-numbers-mean) for what the numbers mean, and [DECISIONS.md](../DECISIONS.md) for why this replaced Evidence.

## Running it locally

From the repo root:

```bash
make dashboard
```

Or directly:

```bash
cd dashboards
uv run --with-requirements requirements.txt streamlit run app.py
```

`warehouse.py` builds `data/nordmarkt.duckdb` itself (the same generator → dlt → dbt steps `make demo` runs) the first time any page is opened, if it doesn't already exist, then every page just queries it.

## Deploying

Hosted for free on [Streamlit Community Cloud](https://streamlit.io/cloud), which needs its own account (see DECISIONS.md) — this isn't wired into the repo's own GitHub Actions/Pages build the way the dbt docs site is.

One-time setup: connect the repo on share.streamlit.io, set **Main file path** to `dashboards/app.py`. Streamlit Cloud reads `dashboards/requirements.txt` (it doesn't understand the root `pyproject.toml`/`uv.lock`, since its resolver assumes Poetry's format) — keep it in step with the root `pyproject.toml` by hand.

Every visit after the container's been asleep triggers a full warehouse rebuild (tens of seconds), since `data/nordmarkt.duckdb` is a gitignored build artifact, not something committed. That's the tradeoff for a fully static, account-free approach not being available here — see DECISIONS.md.
