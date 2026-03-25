# Deploying the Demo

A portfolio project nobody can look at is a private hobby. This file covers how Kiezkauf gets in front of people, and the configuration to make it happen.

The guiding constraint: **the permanent demo cannot depend on Snowflake.** The trial expires after 30 days, and a dead link is worse than no link. Everything public runs on DuckDB. Snowflake gets captured, not hosted.

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

Evidence is the piece that makes a free permanent demo possible, and it's the reason it beat Metabase in [STACK.md](STACK.md). Evidence compiles to **static files**. Query results ship to the browser as parquet, and DuckDB compiled to WebAssembly runs them client-side. Filters and drilldowns work. There is no backend and no database server.

That turns the entire warehouse into a build step:

```
GitHub Actions (on push, and nightly)
  generator → dlt → dbt build → dbt docs → evidence build → static site → GitHub Pages
```

One workflow produces one site with two things on it:

- `/` — the Evidence dashboard
- `/docs` — the dbt documentation site, including the lineage graph

For this project the docs URL is arguably the more important of the two, because documentation quality *is* the deliverable. It's where someone sees that every mart column has a real description.

### Why GitHub Pages and not Vercel

I originally leaned Vercel. Once the site is built inside GitHub Actions, though, the host only needs to accept a folder, and Pages does that with no extra account, no extra token, and no third-party service in the loop. Both URLs come from the repo itself.

The one cost is that Pages serves from `username.github.io/kiezkauf-warehouse/`, a subdirectory, so Evidence needs its base path configured. That's the `EVIDENCE_BASE_PATH` line in the workflow below. If it gives trouble, or you want a cleaner URL, Cloudflare Pages takes a prebuilt folder in one command:

```bash
npx wrangler pages deploy ./site --project-name kiezkauf
```

Netlify and Vercel both have equivalents. The build steps don't change, only the last one.

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
      EVIDENCE_BASE_PATH: /kiezkauf-warehouse
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

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: dashboards/package-lock.json

      - name: Build the dashboard
        working-directory: dashboards
        run: |
          npm ci
          npm run sources
          npm run build

      - name: Assemble the site
        run: |
          mkdir -p site/docs
          cp -r dashboards/build/* site/
          cp target/static_index.html site/docs/index.html

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

Later projects extend this with Snowflake pull request environments built on zero-copy clones and `--select state:modified+ --defer`. Stage one doesn't need that, and adding it before there's a slow build to speed up would be solving a problem you don't have.

---

## Clone and run

Target: a stranger gets a working warehouse in under two minutes with no accounts.

`Makefile` (the real one — see the repo root)

```make
.PHONY: demo generate deps load snapshot mutate build docs full snowflake clean

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

full:
	uv run python generator/generate.py --profile full --seed 42

snowflake:
	uv run python pipeline/load.py --target snowflake
	uv run dbt snapshot --target snowflake
	uv run dbt build --target snowflake

clean:
	rm -rf target dbt_packages data/generated data/*.duckdb*
```

There's no `dash` target yet — the Evidence dashboard doesn't exist until Stage 3.

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
  "name": "Kiezkauf Warehouse",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "features": {
    "ghcr.io/devcontainers/features/node:1": { "version": "20" }
  },
  "postCreateCommand": "curl -LsSf https://astral.sh/uv/install.sh | sh && ~/.local/bin/uv sync",
  "forwardPorts": [3000, 8080],
  "portsAttributes": {
    "3000": { "label": "Evidence dashboard" },
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

If the numbers on the public dashboard don't match what a reviewer gets when they run it locally, the project looks broken, and they won't email to ask why. `--seed 42` appears in every command above for exactly this reason.

---

## Two dataset sizes

Evidence ships parquet to the browser, so a large dataset makes the public page slow. But Snowflake cost and performance numbers are meaningless at small volumes.

Two profiles in the generator solve it:

| Profile | Rough size | Used for |
|---|---|---|
| `demo` | ~5k customers, ~50k order lines | Public site, CI, Codespaces |
| `full` | ~50k customers, ~500k order lines | Snowflake runs, cost and performance work |

Same models, same tests, same seed. Only the volume changes.

---

## Snowflake: a recording window, not a host

Snowflake can't be in the permanent demo, so treat the 30-day trial as a window for **capturing evidence of things DuckDB cannot show**.

While the trial is live, collect:

- the query profile on the heaviest model
- warehouse sizing and credit consumption before and after tuning
- a clustering key comparison, with pruning statistics
- cost attribution from `ACCOUNT_USAGE`
- a short screen recording of `dbt build --target snowflake` running end to end

These go in the README under *Running on Snowflake*. Screenshots are permanent; the account isn't.

### If you're actively interviewing

It's worth roughly €25 a month to keep a small account alive so you can run live if asked. A weekly scheduled run keeps recent query history in `ACCOUNT_USAGE`, which is what the FinOps project later feeds on.

`.github/workflows/snowflake-weekly.yml`

```yaml
name: Snowflake weekly

on:
  schedule:
    - cron: "0 5 * * 1"
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      DBT_PROFILES_DIR: ./
      SNOWFLAKE_ACCOUNT: ${{ secrets.SNOWFLAKE_ACCOUNT }}
      SNOWFLAKE_USER: ${{ secrets.SNOWFLAKE_USER }}
      SNOWFLAKE_ROLE: TRANSFORMER
      SNOWFLAKE_WAREHOUSE: WH_XS
      SNOWFLAKE_DATABASE: KIEZKAUF
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen

      - name: Write the private key
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SNOWFLAKE_PRIVATE_KEY }}" > ~/.ssh/snowflake_key.p8
          chmod 600 ~/.ssh/snowflake_key.p8

      - run: uv run python generator/generate.py --profile full --seed 42
      - run: uv run dlt pipeline kiezkauf run --destination snowflake
      - run: uv run dbt deps && uv run dbt build --target snowflake
```

**Use key-pair authentication, not a password.** It's a small thing and reviewers notice it. Snowflake is also deprecating single-factor password auth for service users, so it's the correct answer regardless.

Secrets needed: `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PRIVATE_KEY`. Nothing else, and none of them ever touch the repo.

---

## The interview demo

Rehearse a three-minute walkthrough. Run it from `make demo` locally, never from the internet.

1. **The lineage graph** in dbt docs. Sources on the left, marts on the right, the shape of the thing in one picture.
2. **One model**, `fct_order_lines`. The grain declared in the first comment, the shipping allocation, the column descriptions.
3. **`DECISIONS.md`**. Pick the order-line-grain entry and explain the tradeoff you accepted.
4. **`dbt build` running live.** It takes seconds on DuckDB.
5. **A failing test.** Break a business rule on purpose and show the error message. This is the part people remember, because it proves the tests do something.

Three rules: never depend on the internet, never depend on the Snowflake trial, and always know what the last command printed.

---

## Checklist

- [ ] Pages enabled, Source set to GitHub Actions
- [ ] `demo.yml` green, site live
- [ ] `ci.yml` green, badge in README
- [ ] Both URLs linked at the top of the README
- [ ] Devcontainer committed, Codespaces button verified
- [ ] `make demo` works from a clean clone on a machine that isn't yours
- [ ] Generator seeded, seed committed
- [ ] Snowflake screenshots captured before the trial expires
- [ ] Three-minute walkthrough rehearsed out loud

---

## What it costs

GitHub Pages, GitHub Actions and Codespaces are free at this scale. Public repositories get unlimited Actions minutes on standard runners, and this build takes a couple of minutes.

Snowflake is the only real expense, and only if you choose to keep it alive past the trial.

**Permanent hosting: €0.**
