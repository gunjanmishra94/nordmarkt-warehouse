# Deploying the Demo

A portfolio project nobody can look at is a private hobby. This file covers how Nordmarkt gets in front of people, and the configuration to make it happen.

The guiding constraint: **the permanent demo cannot depend on an account only I have.** Everything public runs on DuckDB.

---

## Three audiences

They want different things, and only building for one of them is the usual mistake.

| Who | Time they'll give it | What they need |
|---|---|---|
| Recruiter, hiring manager | 90 seconds | A URL. They will not clone anything. |
| Engineer reviewing the repo | 10 minutes | `git clone` and one command that works |
| Me, in an interview | 3 minutes, live | Fast, offline, impossible to break |

---

## How the public demo works

This section originally described Evidence compiling to static files with DuckDB-via-WASM running entirely in the browser — no backend, deployable to GitHub Pages for free. That's no longer how Evidence works, and Evidence Studio (what replaced it) turned out to have no permanent free tier at all; both it and the MotherDuck connection it required were dropped in favor of a Streamlit dashboard. Full story in DECISIONS.md.

So the split is:

- **This repo's own GitHub Pages site** (below) is the dbt documentation site, including the lineage graph — arguably the more important of the two anyway, since documentation quality *is* the deliverable. It's where someone sees that every mart column has a real description.
- **The Streamlit dashboard** is hosted by Streamlit Community Cloud once connected, at whatever URL it assigns. Linked from the README once that's set up; not built by our CI. See `dashboards/README.md` for how it's deployed and why it rebuilds the warehouse itself on a cold start.

```
GitHub Actions (on push, and nightly)
  generator → dlt → dbt build (twice, for real snapshot history) → dbt docs → GitHub Pages
```

### Why GitHub Pages and not Vercel

I originally leaned Vercel. Once the site is built inside GitHub Actions, though, the host only needs to accept a folder, and Pages does that with no extra account, no extra token, and no third-party service in the loop. Both URLs come from the repo itself.

The one cost is that Pages serves from `username.github.io/nordmarkt-warehouse/`, a subdirectory. dbt's static docs don't care about base paths, so that's no longer a concern now that the dashboard isn't part of this build.

---

## The main workflow

`.github/workflows/demo.yml`

```yaml
name: Demo site

on:
  push:
    branches: [main]
  schedule:
    - cron: "0 4 * * *"   # nightly, so the site never looks stale
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      DBT_PROFILES_DIR: ./
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - name: Install Python dependencies
        run: uv sync --frozen

      - name: Generate the demo dataset
        run: uv run python generator/generate.py --profile demo --seed 42

      - name: Load raw data
        run: uv run python pipeline/load.py --target duckdb

      - name: Install dbt packages
        run: uv run dbt deps

      - name: Build the warehouse (baseline extract)
        run: uv run dbt build --target duckdb

      # dim_customer's Type-2 history needs two real extracts to snapshot a
      # diff between — see DECISIONS.md. This simulates the second one.
      - name: Simulate a later day for a slice of customers
        run: uv run python generator/mutate_customers.py --seed 43

      - name: Reload and rebuild (captures the customer snapshot diff)
        run: |
          uv run python pipeline/load.py --target duckdb
          uv run dbt build --target duckdb

      - name: Generate dbt docs
        run: uv run dbt docs generate --target duckdb --static

      - name: Assemble the site
        run: |
          mkdir -p site
          cp target/static_index.html site/index.html

      - uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - id: deploy
        uses: actions/deploy-pages@v4
```

Two details worth pointing out.

`dbt docs generate --static` produces `target/static_index.html`, a single self-contained file with the manifest embedded. Much easier to host than the multi-file version.

The nightly schedule exists purely so the site never looks abandoned. A dashboard whose latest data is from four months ago reads as a project you gave up on.

**One-time setup:** repo Settings → Pages → Source → *GitHub Actions*. That's it. No tokens, no secrets.

---

## Pull request checks

`.github/workflows/ci.yml`

```yaml
name: CI

on:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      DBT_PROFILES_DIR: ./
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --frozen
      - run: uv run pre-commit run --all-files
      - run: uv run python generator/generate.py --profile demo --seed 42
      - run: uv run python pipeline/load.py --target duckdb
      - run: uv run dbt deps
      - run: uv run dbt build --target duckdb
      - run: uv run python generator/mutate_customers.py --seed 43
      - run: uv run python pipeline/load.py --target duckdb
      - run: uv run dbt build --target duckdb
```

This is what makes the green badge in the README mean something. Every pull request generates data, builds every model and runs every test from scratch in about a minute, entirely free.

---

## Clone and run

Target: a stranger gets a working warehouse in under two minutes with no accounts.

`Makefile` (the real one — see the repo root)

```make
.PHONY: demo generate deps load snapshot mutate build docs full clean

export DBT_PROFILES_DIR := .

# dim_customer's Type-2 history needs at least two real extracts to snapshot
# a diff between. `dbt build` already runs the snapshot in DAG order (after
# staging, before the marts that depend on it), so this runs build once
# against the baseline data, mutates a slice of customers to simulate a
# later day, then builds again to capture the diff. Repeated targets are
# invoked as recursive sub-makes since make dedupes repeated prerequisites.
demo: generate deps
	$(MAKE) load
	$(MAKE) build
	$(MAKE) mutate
	$(MAKE) load
	$(MAKE) build

generate:
	uv run python generator/generate.py --profile demo --seed 42

deps:
	uv run dbt deps

load:
	uv run python pipeline/load.py --target duckdb

snapshot:
	uv run dbt snapshot --target duckdb

mutate:
	uv run python generator/mutate_customers.py --seed 43

build:
	uv run dbt build --target duckdb

docs:
	uv run dbt docs generate --target duckdb && uv run dbt docs serve

dashboard:
	cd dashboards && uv run --with-requirements requirements.txt streamlit run app.py

full:
	uv run python generator/generate.py --profile full --seed 42

clean:
	rm -rf target dbt_packages data/generated data/*.duckdb*
```

`make dashboard` builds the warehouse itself on first load if it doesn't already exist, so it works standalone too — see `dashboards/README.md` for how it's deployed to Streamlit Community Cloud.

So the README instruction is two lines:

```bash
uv sync
make demo
```

### Codespaces

Add a devcontainer and reviewers get an **Open in GitHub Codespaces** button. They click it and your project is running in a browser tab with nothing installed on their machine. One JSON file, and it meaningfully raises the odds someone actually runs the thing.

`.devcontainer/devcontainer.json`

```json
{
  "name": "Nordmarkt Warehouse",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "postCreateCommand": "curl -LsSf https://astral.sh/uv/install.sh | sh && ~/.local/bin/uv sync",
  "forwardPorts": [8501, 8080],
  "portsAttributes": {
    "8501": { "label": "Streamlit dashboard (make dashboard)" },
    "8080": { "label": "dbt docs" }
  },
  "customizations": {
    "vscode": {
      "extensions": [
        "innoverio.vscode-dbt-power-user",
        "dorzey.vscode-sqlfluff",
        "ms-python.python"
      ]
    }
  }
}
```

---

## Determinism

The generator must be seeded, and the seed must be committed.

If the numbers on the public dbt docs / dashboard don't match what a reviewer gets when they run it locally, the project looks broken, and they won't email to ask why. `--seed 42` appears in every command above for exactly this reason.

---

## Two dataset sizes

A large dataset makes CI and the dev loop slow for no benefit, but a bigger one is still useful for exercising the incremental/backfill logic at a realistic scale.

Two profiles in the generator solve it:

| Profile | Rough size | Used for |
|---|---|---|
| `demo` | ~5k customers, ~50k order lines | Public site, CI, Codespaces |
| `full` | ~50k customers, ~500k order lines | Local performance/backfill work |

Same models, same tests, same seed. Only the volume changes.

---

## The interview demo

Rehearse a three-minute walkthrough. Run it from `make demo` locally, never from the internet.

1. **The lineage graph** in dbt docs. Sources on the left, marts on the right, the shape of the thing in one picture.
2. **One model**, `fct_order_lines`. The grain declared in the first comment, the shipping allocation, the column descriptions.
3. **`DECISIONS.md`**. Pick the order-line-grain entry and explain the tradeoff you accepted.
4. **`dbt build` running live.** It takes seconds on DuckDB.
5. **A failing test.** Break a business rule on purpose and show the error message. This is the part people remember, because it proves the tests do something.

Two rules: never depend on the internet, and always know what the last command printed.

---

## Checklist

- [ ] Pages enabled, Source set to GitHub Actions
- [ ] `demo.yml` green, site live
- [ ] `ci.yml` green, badge in README
- [ ] Both URLs linked at the top of the README
- [ ] Devcontainer committed, Codespaces button verified
- [ ] `make demo` works from a clean clone on a machine that isn't yours
- [ ] Generator seeded, seed committed
- [ ] Three-minute walkthrough rehearsed out loud

---

## What it costs

GitHub Pages, GitHub Actions and Codespaces are free at this scale. Public repositories get unlimited Actions minutes on standard runners, and this build takes a couple of minutes.

**Permanent hosting: €0.**
