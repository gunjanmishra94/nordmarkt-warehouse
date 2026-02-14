# Dashboard

Two builds of the same three pages (revenue overview, category trends, fulfilment timing), sharing one set of SQL (`queries.py`). See the main [README](../README.md#what-the-numbers-mean) for what the numbers mean, and [DECISIONS.md](../DECISIONS.md) for why there are two builds and why this replaced Evidence.

| | `app.py` + `pages/` (this folder) | `static/` |
|---|---|---|
| Runs on | Streamlit Community Cloud | GitHub Pages, at `/dashboard/` |
| Needs an account | Yes (Streamlit Cloud, and MotherDuck when deployed) | No |
| Data | Live — local dev queries `data/nordmarkt.duckdb` directly; deployed, queries MotherDuck | A snapshot — precomputed JSON, refreshed on every CI build |
| How | Real Python process, real DuckDB (or MotherDuck) connection | Runs Streamlit *in the browser* via [stlite](https://github.com/whitphx/stlite) (Pyodide/WebAssembly) — no server at all |

## Running the live version locally

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

## Deploying the live version

Hosted for free on [Streamlit Community Cloud](https://streamlit.io/cloud), which needs its own account (see DECISIONS.md) — this isn't wired into the repo's own GitHub Actions/Pages build the way the static version and the dbt docs site are.

One-time setup: connect the repo on share.streamlit.io, set **Main file path** to `dashboards/app.py`. Streamlit Cloud reads `dashboards/requirements.txt` (it doesn't understand the root `pyproject.toml`/`uv.lock`, since its resolver assumes Poetry's format) — keep it in step with the root `pyproject.toml` by hand. In the app's **Secrets**, set `MOTHERDUCK_TOKEN` (and `MOTHERDUCK_DATABASE` if it's not `nordmarkt`) to a MotherDuck [service token](https://motherduck.com/docs/key-tasks/authenticating-and-connecting/authenticating-to-motherduck/#authentication-using-a-service-token).

With `MOTHERDUCK_TOKEN` set, `warehouse.py` connects straight to MotherDuck instead of building a local file — no cold-start rebuild. That database is kept fresh independently by `.github/workflows/motherduck.yml` (nightly and on push to `main`), which needs the same token as a repo secret. See DECISIONS.md for why MotherDuck is back after being dropped once already.

## The static version (`static/`)

Runs entirely client-side: `static/index.html` loads [stlite](https://github.com/whitphx/stlite) from a CDN, which boots the real Streamlit package inside a Pyodide (WebAssembly) Python runtime in the visitor's browser — no server, no account, works offline once loaded. `static/app.py` and `static/pages/*.py` are near-identical to the live versions, except they read `static/data/*.json` (via `static/data_source.py`) instead of querying DuckDB directly, since DuckDB doesn't run inside that browser runtime.

`static/build_data.py` produces those JSON files. It's not run by hand — `.github/workflows/demo.yml` runs it right after `dbt build`, using the exact same queries (`queries.py`) the live app runs, and copies `static/` into the site published to GitHub Pages. So the static dashboard is a snapshot from the last CI run, refreshed nightly and on every push, not live — the caption on its first page says so.

Tested end-to-end in a real, headless Chromium browser during development (Playwright): all three pages render with correct numbers matching the live version. One known cosmetic issue: the line/bar charts log a harmless `Infinite extent` warning to the browser console (an Altair/Vega-Lite quirk in the Streamlit version stlite currently bundles) — doesn't affect what's rendered.
