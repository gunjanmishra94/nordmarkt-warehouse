# The Stack, and Why

Every tool here had to justify itself against two questions: does it teach me something an analytics engineering job will ask for, and can a stranger run this repo without an account or a credit card?

Where those two pulled in opposite directions, I say so below rather than pretending there was no tension.

---

## Summary

| Job | Tool | One-line reason |
|---|---|---|
| Transformation | dbt Core | The job is called analytics engineering because of this tool |
| Warehouse | DuckDB | No account, no cost, runs anywhere |
| Loading | dlt | Python library, no infrastructure, code you can read |
| Data generation | Python + Faker + Pydantic | Total control over how messy the input is |
| Testing | dbt tests, dbt_utils, dbt_expectations | Three layers of checks, from schema to statistics |
| Project linting | dbt_project_evaluator | Catches modelling mistakes I can't see myself |
| Formatting | SQLFluff, Ruff, pre-commit | Removes style from code review entirely |
| Dashboard | Streamlit | Python, in the repo, deploys free on Streamlit Community Cloud |
| Environment | uv | Fast, reproducible, one file |
| CI | GitHub Actions | Free, and the green tick is part of the portfolio |

---

## The main decisions

### dbt Core, not dbt Cloud or dbt Fusion

dbt is the centre of the project, so this one mattered most.

**dbt Core** is the free, Apache-licensed command-line version. Everything runs locally, nothing is hidden behind a login, and anyone can clone the repo and get identical behaviour.

**dbt Cloud** has a nicer interface and some genuinely useful features locked behind it, notably the hosted semantic layer. But a portfolio project that requires a reviewer to sign up for a SaaS account is a portfolio project nobody looks at.

**dbt Fusion** is the newer engine, rewritten in Rust. It's dramatically faster and the editor experience is better. It also has a more restrictive licence and narrower adapter support, which makes it the wrong base for a public repo today. I'll run it locally alongside Core so I can speak to the difference, because with dbt Labs and Fivetran now under one roof this is a live topic and interviewers bring it up.

**Verdict:** Core is the safe, portable choice. Being able to explain why Fusion exists is worth more than using it.

### DuckDB only, not Snowflake as well

Earlier drafts of this project targeted Snowflake and DuckDB together — the classic "prove it on the real thing, develop on the free thing" split, including adapter-dispatch macros to isolate the two dialects' differences. Snowflake itself was dropped from this project; see DECISIONS.md.

The reason is the same one the two-adapter design was trying to work around: Snowflake is a 30-day trial with $400 of credits, after which the project either costs money forever or the "prove it on Snowflake" checklist items just sit unchecked indefinitely. That's exactly what happened here — no trial account was ever created, so every Snowflake-shaped line in this repo (a second `profiles.yml` target, `dbt-snowflake`, adapter-dispatch macros with a `snowflake__` variant nothing ever exercised) was speculative work carried for a warehouse the project never actually touched.

DuckDB runs inside the Python process. No server, no credentials, no cost, and every model, test and doc in this repo has actually been built and verified against it. That's the whole warehouse story: **DuckDB proves the modelling**, full stop — nothing else in this project talks to a hosted warehouse. (An earlier draft added MotherDuck solely because Evidence Studio needed a live server-side connection; both are gone now — see DECISIONS.md.)

If Snowflake experience needs demonstrating for a job search, that belongs in a project built around Snowflake-only concerns (warehouse sizing, clustering keys, `ACCOUNT_USAGE`) from the start, funded and run inside a live trial window — not bolted onto a project that has to keep working after the trial ends.

### dlt for loading, not Fivetran or Airbyte

The loading step here is small: move generated files into the warehouse, and pull daily exchange rates from a public API.

**Fivetran** is the market leader and a useful name to have touched. It's also a hosted service, so it can't live in the repo, and pointing it at locally-generated files makes no sense.

**Airbyte** open source can be self-hosted, but running it means Docker Compose, several containers and a meaningful chunk of a weekend. That effort buys nothing this project needs.

**dlt** is just a Python library. `pip install`, write a function, get schema inference, incremental loading and state management for free. The loading code sits in the repo next to everything else where a reviewer can actually read it.

**Verdict:** dlt, because the loading step isn't the interesting part and shouldn't eat a week. If I want the Fivetran name on my CV I'll wire up one connector on their free tier separately.

### Generated data, not a public dataset

The obvious alternative is grabbing a public e-commerce dataset. I decided against it.

Public datasets are clean, or at least clean in ways someone else already decided. This project is partly *about* handling mess, and a generator lets me choose exactly which mess to handle: duplicate order IDs, events that arrive three days late, timestamps in three timezones, a column renamed halfway through history.

Every one of those is a deliberate test case, and because I built the generator I know the correct answer and can assert against it. With a public dataset you're guessing.

The risk is that generated data reads as fake and unimpressive. The defence is that the generator is itself a piece of the work — it's in the repo, it's documented, and the mess it creates is more realistic than most public datasets.

### Streamlit for dashboards, not Evidence, Metabase or Looker

**Looker** is the tool Berlin scaleups list in job ads. It has no free tier. I'll learn LookML syntax on paper and not pretend otherwise.

**Metabase** is free and open source, but the dashboards live in its own database. They can't be reviewed in a pull request, and they don't survive a clone.

**Evidence** writes dashboards as markdown files with SQL in them, which sit in the repo and get code-reviewed like anything else — the original pick, for exactly that reason. It didn't survive contact with reality: Evidence pivoted from a free static-site generator to a hosted product ("Evidence Studio") mid-project, and Evidence Studio turned out to have no permanent free tier at all — a 30-day trial, then $2,500/month. Full story, including the Observable Framework alternative that got built and then dropped too, in DECISIONS.md.

**Streamlit** writes dashboards as plain Python, which is the language everything else non-SQL in this repo is already written in — no new toolchain, and a reviewer reads `dashboards/app.py` the same way they'd read `generator/generate.py`. Deploys free, permanently, on Streamlit Community Cloud.

**Verdict:** Streamlit, because it's free forever (not a trial) and it's the one option here that doesn't ask this all-Python project to also learn an npm-based framework. The cost is that Streamlit needs a live Python process rather than serving static files, so the dashboard rebuilds the warehouse itself on a cold start instead of loading an instantly-static page.

**Update:** there's now a second build, `dashboards/static/`, using [stlite](https://github.com/whitphx/stlite) to run the same Streamlit pages entirely in the browser (Pyodide/WebAssembly) — a genuinely static, account-free alternative deployed to GitHub Pages, at the cost of serving a data snapshot from the last CI build rather than a live connection. Both builds exist side by side. Full reasoning in DECISIONS.md.

---

## What DuckDB actually is

An embedded analytical database. Think SQLite, but columnar and vectorised for aggregate queries instead of row-at-a-time transactional ones. It runs inside the Python process. No server, no port, no connection pool.

The entire warehouse is one file, `data/nordmarkt.duckdb`. Delete it and the warehouse is gone; copy it and you've cloned the warehouse. It's gitignored, because it's a binary that changes on every run and `make demo` rebuilds it in seconds.

For this data it's also plenty of engine: the `full` profile is around 500k order lines, and DuckDB comfortably handles hundreds of millions of rows on a laptop with no network round trip to slow it down.

---

## The testing layers

Three tools, because they catch genuinely different things.

**dbt's built-in tests** cover structure. Is this key unique, is this column ever null, does every `customer_id` in the orders table actually exist in the customer table. Cheap, fast, and they should always be green.

**dbt_utils** adds the common patterns that everyone writes by hand otherwise, like checking that two tables have the same row count or that a set of columns is unique in combination.

**dbt_expectations** covers distributions. These catch the failures that structural tests sail straight past: revenue is technically a valid number today, it's just forty times yesterday's. Borrowed from the Python Great Expectations library.

On top of those sit **singular tests**, which are just SQL queries that should return zero rows. This is where the domain knowledge goes. Refunds must never exceed the original order value. No parcel is delivered before it was ordered. Allocated shipping across order lines must sum back to the shipping actually charged.

That last category is the one that matters. Anyone can assert a column is unique. Asserting that the business rules hold is the part that proves you understood the business.

And **dbt_project_evaluator** sits outside all of this, checking the project rather than the data: models that join directly to sources, dimensions referenced from the wrong layer, tables nothing depends on. It's an automated code review from someone who has seen a thousand dbt projects.

---

## Supporting cast

**uv** for Python environments. Faster than pip by a wide margin, locks dependencies properly, and one `uv sync` gets a stranger to a working setup.

**Pydantic** in the generator. The schemas that define what a valid order looks like double as the documented contract for what the raw layer should contain.

**SQLFluff, Ruff and pre-commit.** Formatting arguments are a waste of a code review. These settle it before the commit lands.

**GitHub Actions.** Runs `dbt build` against DuckDB on every pull request, so the badge in the README means something.

---

## Deliberately not in the stack

Restraint is part of the design, so here's what got left out.

**Docker.** The most common question about this list, so it goes first.

Docker's job is isolating and networking long-running services. This project has none. DuckDB is a library that runs inside the Python process, not a server, so there is no daemon to start and no port to expose. `uv` already pins the Python version and locks every dependency, which covers reproducibility. And the devcontainer in [DEPLOY.md](DEPLOY.md) already runs the whole project in a container built from a maintained base image, so reviewers get isolation without me writing or maintaining a Dockerfile.

Adding it would cost real iteration speed, because volume-mounted filesystem I/O on a Mac is slow and every dependency change triggers a rebuild. It would also contradict the two entries below: arguing that Spark is overkill for laptop-sized data, then containerising two CLIs, is not a consistent position.

There is one version of this project where Docker earns its place. If the generator wrote to a real Postgres instance standing in as Nordmarkt's operational database, dlt would be doing genuine replication with watermarks and soft deletes rather than reading files, which is a better story for the ingestion layer. If I add that, it goes in as an optional path — `make demo` stays file-based so the clone-and-run promise holds, and `make demo-postgres` spins up the container for anyone who wants it.

**Airflow or Dagster.** There's nothing to orchestrate yet. One `dbt build` on a schedule is a GitHub Actions cron line, not a reason to stand up a scheduler. Dagster arrives when a later project actually needs asset-level scheduling.

**Spark.** The data fits comfortably on a laptop. Reaching for Spark here would signal that I reach for Spark by reflex, which is the opposite of the impression I want.

**Kafka or streaming.** Daily batch is the correct answer for this business. Building streaming into it would be architecture theatre.

**A semantic layer.** Coming in a later project. Adding it now would mean building metric definitions before the underlying tables have settled, which is the wrong order.

**Snowflake.** It was in an earlier draft of this stack (see DECISIONS.md for why it was dropped): a 30-day trial that either costs money forever or leaves the "prove it on Snowflake" checklist item unchecked indefinitely, which is what actually happened. If Snowflake experience needs proving, that's a project built and funded around Snowflake-only concerns from the start, not a second target bolted onto one that has to keep working for free after the trial ends.

Each of these is a tool I could add. Not adding them is the point.

---

## What it costs

Nearly nothing.

DuckDB, dbt Core, dlt, uv and every dbt package here are free and open source. GitHub Actions is free at this volume. Streamlit Community Cloud has a genuine permanent free tier usable at this scale.

**Total: €0.**

---

## Coming in later projects

This file describes what project one needs. The wider portfolio adds:

- **MetricFlow** for governed metric definitions
- **Dagster** for asset-based orchestration
- **Elementary** for freshness and anomaly monitoring
- **Terraform** for Snowflake roles and warehouses as code
- **Anthropic API + MCP** for a natural-language interface that queries the semantic layer rather than writing raw SQL

Each arrives when there's a real reason for it.

---

## A note on versions

Tooling in this space moves quickly, dbt especially. Everything is pinned in `pyproject.toml` and `packages.yml`. If you're reading this long after it was written, check what's current before copying the pins.
