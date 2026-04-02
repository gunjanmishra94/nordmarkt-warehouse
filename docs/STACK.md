# The Stack, and Why

Every tool here had to justify itself against two questions: does it teach me something an analytics engineering job will ask for, and can a stranger run this repo without an account or a credit card?

Where those two pulled in opposite directions, I say so below rather than pretending there was no tension.

---

## Summary

| Job | Tool | One-line reason |
|---|---|---|
| Transformation | dbt Core | The job is called analytics engineering because of this tool |
| Warehouse (real) | Snowflake | What the market actually runs on |
| Warehouse (local) | DuckDB | Keeps the repo runnable after the trial expires |
| Loading | dlt | Python library, no infrastructure, code you can read |
| Data generation | Python + Faker + Pydantic | Total control over how messy the input is |
| Testing | dbt tests, dbt_utils, dbt_expectations | Three layers of checks, from schema to statistics |
| Project linting | dbt_project_evaluator | Catches modelling mistakes I can't see myself |
| Formatting | SQLFluff, Ruff, pre-commit | Removes style from code review entirely |
| Dashboard | Evidence.dev | Charts live in the repo as code, deploy free |
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

### Snowflake *and* DuckDB, not one or the other

This is the biggest architectural decision in the project, and it's the one I'd most want to be asked about.

Snowflake is what the job market asks for. It's also a 30-day trial with $400 of credits, after which the project either costs money forever or stops working. A dead portfolio project is worthless.

DuckDB runs inside the Python process. No server, no credentials, no cost. A reviewer clones the repo and has a working warehouse in seconds.

So the project targets both. The same models, tests and documentation run against either, selected with a flag. Where the two databases genuinely differ, the difference is isolated in a macro rather than smeared across the models.

The honest cost: supporting two adapters is real extra work, and a couple of Snowflake-specific things (clustering keys, warehouse sizing, `ACCOUNT_USAGE`) simply have no DuckDB equivalent and are skipped locally.

The payoff is threefold and worth the tax. The repo stays alive forever. Local development is fast and free, so I only spend Snowflake credits on runs that are worth spending them on. And writing genuinely cross-adapter dbt is a harder skill than writing dbt for one warehouse, which makes it something to talk about rather than something to apologise for.

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

### Evidence.dev for dashboards, not Metabase or Looker

**Looker** is the tool Berlin scaleups list in job ads. It has no free tier. I'll learn LookML syntax on paper and not pretend otherwise.

**Metabase** is free and open source, but the dashboards live in its own database. They can't be reviewed in a pull request, and they don't survive a clone.

**Evidence** writes dashboards as markdown files with SQL in them. They sit in the repo, they get code-reviewed like anything else. A reviewer can read the chart's query without opening a tool.

**Verdict:** Evidence, because "the dashboard is in the repo" fits everything else about this project — though not for the reason below anymore.

**Update, Stage 3:** the free/static/no-login version above ("Legacy Evidence") is deprecated. Current Evidence ("Studio") needs a live connection to one warehouse and its own account; the closest fit for us is MotherDuck (hosted DuckDB, its own free tier), used as that connection. Full reasoning in DECISIONS.md — the short version is that everything else about the choice still holds (markdown+SQL, in the repo, reviewable), it's just no longer the login-free static build originally described here.

---

## Writing dbt for two warehouses

The decision to target Snowflake and DuckDB together is explained above. This is what it means in practice, because it's the part interviewers push on.

### What DuckDB actually is

An embedded analytical database. Think SQLite, but columnar and vectorised for aggregate queries instead of row-at-a-time transactional ones. It runs inside the Python process. No server, no port, no connection pool.

The entire warehouse is one file, `data/kiezkauf.duckdb`. Delete it and the warehouse is gone; copy it and you've cloned the warehouse. It's gitignored, because it's a binary that changes on every run and `make demo` rebuilds it in seconds.

### Is DuckDB alone enough?

For this data, honestly, yes. The `full` profile is around 500k order lines. DuckDB handles hundreds of millions of rows on a laptop, and at this scale it's *faster* than Snowflake because there's no network round trip.

So Snowflake isn't here for capability. It's here because it's what job ads ask for, and because it has properties DuckDB structurally cannot have: warehouse sizing and auto-suspend, roles and RBAC, clustering keys and partition pruning, zero-copy clones, cost attribution through `ACCOUNT_USAGE`, real concurrency. Those aren't missing features, they're consequences of being a multi-tenant cloud service. A later project in this portfolio is built entirely out of them.

The short version: **DuckDB proves the modelling, Snowflake proves the platform skills.**

### The differences that bite

Four things account for most of the friction.

**Identifier casing.** Snowflake folds unquoted identifiers to uppercase; DuckDB preserves them as written. The fix is discipline rather than cleverness: lowercase everywhere, never quote an identifier.

**Types.** Snowflake's `VARIANT` and `NUMBER` have no exact DuckDB equivalent. Use `JSON` and an explicit `DECIMAL(p, s)`, and never rely on a default precision.

**Date functions.** `dateadd` and `datediff` take different argument styles. Wrap them once in a macro and stop thinking about it.

**Incremental strategies.** `dbt-duckdb` supports the common ones but not identically to `dbt-snowflake`. The merge logic gets tested on both targets in Stage 3, early, rather than discovering the gap at the end.

### The rule for handling them

When the two genuinely differ, isolate the difference in a macro using dbt's adapter dispatch. Do not scatter `{% if target.type == 'snowflake' %}` through the models.

The difference matters. Scattered conditionals mean every model has to be read twice and the divergence spreads silently. Dispatch keeps the models warehouse-agnostic and puts every difference in one reviewable place. It's also a technique most dbt users have never needed, which makes it worth being able to explain.

### If Snowflake becomes inconvenient

**MotherDuck** is hosted DuckDB with a free tier and the same adapter. It doesn't replace Snowflake on a CV, but it's a drop-in third target if the demo ever needs to query something remote rather than local.

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

**GitHub Actions.** Runs `dbt build` against DuckDB on every pull request, so the badge in the README means something. Later projects add Snowflake pull-request environments using zero-copy clones, but stage one doesn't need that.

---

## Deliberately not in the stack

Restraint is part of the design, so here's what got left out.

**Docker.** The most common question about this list, so it goes first.

Docker's job is isolating and networking long-running services. This project has none. DuckDB is a library that runs inside the Python process, not a server, so there is no daemon to start and no port to expose. `uv` already pins the Python version and locks every dependency, which covers reproducibility. And the devcontainer in [DEPLOY.md](DEPLOY.md) already runs the whole project in a container built from a maintained base image, so reviewers get isolation without me writing or maintaining a Dockerfile.

Adding it would cost real iteration speed, because volume-mounted filesystem I/O on a Mac is slow and every dependency change triggers a rebuild. It would also contradict the two entries below: arguing that Spark is overkill for laptop-sized data, then containerising two CLIs, is not a consistent position.

There is one version of this project where Docker earns its place. If the generator wrote to a real Postgres instance standing in as Kiezkauf's operational database, dlt would be doing genuine replication with watermarks and soft deletes rather than reading files, which is a better story for the ingestion layer. If I add that, it goes in as an optional path — `make demo` stays file-based so the clone-and-run promise holds, and `make demo-postgres` spins up the container for anyone who wants it.

**Airflow or Dagster.** There's nothing to orchestrate yet. One `dbt build` on a schedule is a GitHub Actions cron line, not a reason to stand up a scheduler. Dagster arrives when a later project actually needs asset-level scheduling.

**Spark.** The data fits comfortably on a laptop. Reaching for Spark here would signal that I reach for Spark by reflex, which is the opposite of the impression I want.

**Kafka or streaming.** Daily batch is the correct answer for this business. Building streaming into it would be architecture theatre.

**A semantic layer.** Coming in a later project. Adding it now would mean building metric definitions before the underlying tables have settled, which is the wrong order.

Each of these is a tool I could add. Not adding them is the point.

---

## What it costs

Nearly nothing.

DuckDB, dbt Core, dlt, uv and every dbt package here are free and open source. GitHub Actions is free at this volume. Evidence Studio and MotherDuck both have free tiers usable at this scale.

Snowflake is the only line item: a 30-day trial with $400 of credits, then roughly €20 to €30 a month if I keep it warm. The plan is to develop on DuckDB first and only start the trial once there's something worth running, which stretches the window to cover the whole build. After it expires the project keeps working locally.

**Total: under €50 for the entire thing, and plausibly €0.**

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
