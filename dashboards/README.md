# Dashboard

A three-page Streamlit app (revenue overview, category trends, fulfilment timing). See the main [README](../README.md#what-the-numbers-mean) for what the numbers mean, and [DECISIONS.md](../DECISIONS.md) for why this replaced Evidence, and why it's backed by MotherDuck when deployed.

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

`warehouse.py` checks for `MOTHERDUCK_TOKEN` first. Unset — the normal case locally — it builds `data/nordmarkt.duckdb` itself (the same generator → dlt → dbt steps `make demo` runs) the first time any page is opened, if it doesn't already exist, then every page just queries it.

## Deploying it

Hosted for free on [Streamlit Community Cloud](https://streamlit.io/cloud), which needs its own account (see DECISIONS.md) — this isn't wired into the repo's own GitHub Actions/Pages build the way the dbt docs site is.

One-time setup: connect the repo on share.streamlit.io, set **Main file path** to `dashboards/app.py`. Streamlit Cloud reads `dashboards/requirements.txt` (it doesn't understand the root `pyproject.toml`/`uv.lock`, since its resolver assumes Poetry's format) — keep it in step with the root `pyproject.toml` by hand. In the app's **Secrets**, set `MOTHERDUCK_TOKEN` (and `MOTHERDUCK_DATABASE` if it's not `nordmarkt`) to a MotherDuck [service token](https://motherduck.com/docs/key-tasks/authenticating-and-connecting/authenticating-to-motherduck/#authentication-using-a-service-token).

With `MOTHERDUCK_TOKEN` set, `warehouse.py` connects straight to MotherDuck instead of building a local file — no cold-start rebuild. That database is kept fresh independently by `.github/workflows/motherduck.yml` (nightly and on push to `main`), which needs the same token as a repo secret. See DECISIONS.md for why MotherDuck is back after being dropped once already, and for why the account-free static build that used to live alongside this one is gone.
