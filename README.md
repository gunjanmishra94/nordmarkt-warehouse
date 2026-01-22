# Kiezkauf Warehouse

An analytics warehouse for a fictional Berlin online marketplace, built with dbt on DuckDB.

This repo is a portfolio project. It exists to show that I can take raw, messy operational data and turn it into a small set of clean, well-documented tables that a business person can actually query and trust.

---

## The idea in plain English

Imagine a company called **Kiezkauf**. It's an online marketplace selling homeware across Germany, Austria and Switzerland. Customers place orders, orders get shipped (or cancelled, or refunded), customers move house, change their subscription tier, and occasionally pay in Swiss francs instead of euros.

Kiezkauf's raw data is a mess, as raw data always is. Events arrive late. The same order sometimes appears twice. Timestamps are recorded in three different timezones. Somebody renamed a column six months ago and nobody wrote it down.

The job of this repo is to sit between that mess and the people asking questions like:

- How much did we sell last month, in euros, excluding refunds?
- How many customers are actually active right now?
- Which product categories are growing, and how fast?
- How long does it take us to go from order placed to parcel delivered?

Nobody should have to understand the mess to answer those questions. That's the whole point.

---

## Why I'm building it

I work as a data engineer and I'm moving into analytics engineering. Those two jobs overlap a lot, but they're judged differently. Data engineering is judged on whether the pipeline runs. Analytics engineering is judged on whether the *numbers are right and people trust them*.

So this project deliberately puts the weight on the second thing. There's a real emphasis on:

- deciding what each table means before writing it
- writing down *why* each decision was made
- testing business rules, not just checking for nulls
- documentation a non-engineer could read

The code being clean is table stakes. The judgement is the deliverable.

---

## How it fits together

Data flows through four stages. Each stage has one job.

```
  Generator  ->  Raw  ->  Staging  ->  Marts  ->  Dashboard
  (Python)      (dlt)     (dbt)       (dbt)      (Evidence)
```

**Generator** — A Python script that invents Kiezkauf's history: customers, orders, shipments, refunds. It deliberately introduces realistic problems (duplicates, late-arriving events, a mid-history schema change) so the rest of the project has something real to defend against.

**Raw** — The generated data lands in the warehouse untouched. Nothing is cleaned here. If the source is ugly, the raw layer is ugly, and that's correct. Loaded with `dlt`, which also pulls real daily exchange rates from a public API so the currency conversion isn't fake.

**Staging** — One model per source table. Renames columns to a consistent convention, casts types, converts every timestamp to UTC, removes duplicates. No business logic and no joins. Boring on purpose.

**Marts** — The actual product. A small number of tables shaped so that a business question maps to a single, obvious query. This is where the thinking lives.

**Dashboard** — A handful of Evidence.dev pages proving the marts answer the questions they claim to answer.

Why each of these tools and not the obvious alternatives: see [STACK.md](docs/STACK.md).
How it all gets published so people can actually look at it: see [DEPLOY.md](docs/DEPLOY.md).

---

## What's in the warehouse

The marts follow a **star schema**: a few large "fact" tables recording things that happened, surrounded by smaller "dimension" tables describing the people and things involved.

| Table | What it holds | Question it answers |
|---|---|---|
| `fct_order_lines` | One row per product per order | How much did we sell, of what, to whom |
| `fct_order_fulfilment` | One row per order, tracking its whole lifecycle | Where do orders get stuck, and for how long |
| `dim_customer` | One row per customer per version of their details | Who bought this, and where did they live *at the time* |
| `dim_product` | One row per product | What category, what price band, which supplier |
| `dim_date` | One row per calendar day | Weekday vs weekend, German public holidays, fiscal periods |

Two of these deserve a note.

**`fct_order_lines` is at order-line grain, not order grain.** That means one row per product within an order, so a three-item order produces three rows. This is a deliberate choice: it lets you analyse by product category without unpicking a nested field. The cost is that you have to be careful summing order-level values like shipping, which would otherwise be triple-counted. The model handles this by allocating shipping proportionally across lines, and the tests enforce that the allocated amounts add back up to the original.

**`dim_customer` tracks history.** If a customer moves from Berlin to Munich, most systems would just overwrite the address, and suddenly all their past orders look like they were shipped to Munich. This table keeps both versions with valid-from and valid-to dates, so a report on "sales by city in March" reflects where people actually lived in March. In dimensional modelling this is called a Type 2 slowly changing dimension. It's more work and it's almost always the right call.

---

## What the numbers mean

Every column has a real description in `models/marts/_marts.yml` — this is the short version of the ones people actually ask about.

**"Revenue" means `fct_order_lines.net_revenue_eur`**: quantity × unit price, minus this line's share of the order's discount. Shipping is deliberately excluded — it's cost recovery, not product revenue, though it's still available (`allocated_shipping_eur`) for anything that needs total order economics.

**Everything is in EUR, converted using the rate on the order's date, not today's.** Shipping and discount are the only amounts actually captured in a non-EUR currency (CHF, for Swiss customers) — the product catalog is EUR-denominated throughout. That conversion happens once per order, using the EUR→CHF rate `stg_fx_rates` pulled from the Frankfurter API for that specific date, before shipping/discount get allocated across the order's lines.

**`fct_order_fulfilment` tracks placed → shipped → delivered → refunded** — not the picked stage sometimes used as an example, because the generator never produces a picked event. Duration columns (`hours_placed_to_shipped` etc.) are null until an order reaches that stage.

**Both fact tables are incremental**, reprocessing a trailing window of recent activity on every run rather than a full rebuild, so that upstream rows arriving late (which the generator deliberately creates for shipments and refunds) still get picked up. See `DECISIONS.md` for why, and `macros/backfill_incremental_model.sql` for forcing a full historical reprocess of an older window.

---

## The build plan

Three stages. Each stage ends with something that runs, so the project is never in a half-broken state.

### Stage 1 — Foundations

Get data flowing end to end, even if it's thin.

- [x] Set up the repo: dbt project, folder structure, naming conventions written down
- [x] Configure a `duckdb` target so the project runs locally, free, with no account (Snowflake was considered and dropped — see DECISIONS.md)
- [x] Write the data generator: customers, products, orders, order lines, shipments, refunds
- [x] Add the deliberate mess: duplicate order IDs, events arriving days late, mixed timezones, one renamed column partway through history
- [x] Load it with `dlt`, plus daily EUR/CHF rates from a public API
- [x] Build the staging layer, one model per source
- [x] Add basic tests: primary keys unique and not null, foreign keys valid
- [x] Wire up SQLFluff and pre-commit so formatting is never a discussion

**Done when:** `dbt build` runs green against DuckDB from a clean clone. **Met** — `make demo` builds 7 staging models and passes all 24 schema tests.

### Stage 2 — The star schema

Build the tables people will actually use.

- [x] `dim_date`, including German public holidays by federal state
- [x] `dim_product`
- [x] `dim_customer` as a dbt snapshot, tracking address and tier changes over time
- [x] `fct_order_lines`, with the grain stated explicitly at the top of the model and in the docs
- [x] Allocate shipping and discounts across lines, with a test proving the allocation sums correctly
- [x] Convert everything to EUR using the rate that applied *on the order date*, not today's rate
- [x] Write column-level descriptions for every field in the marts. Every single one.
- [x] Start `DECISIONS.md` and record the choices made so far

**Done when:** someone can answer "revenue by product category by month, in euros" with a single `SELECT`. **Met** — see `models/marts/_marts.yml` and `DECISIONS.md` for the modelling choices behind it.

### Stage 3 — Make it real

The difference between a demo and something you'd put in production.

- [x] Convert `fct_order_lines` to an incremental model so it doesn't rebuild from scratch every run
- [x] Handle late-arriving events properly with a lookback window, and write a backfill macro
- [x] Build `fct_order_fulfilment` as an accumulating snapshot, tracking each order through placed → picked → shipped → delivered with durations between each step
- [x] Add business-rule tests: refunds never exceed order value, no delivery date before its order date, no negative quantities
- [x] Add distribution tests with `dbt_expectations` to catch the day revenue silently triples
- [ ] Publish dbt docs and the dashboard to GitHub Pages (see [DEPLOY.md](docs/DEPLOY.md))
- [x] Build three Evidence pages: revenue overview, category trends, fulfilment timing
- [x] Write the README section explaining what the numbers mean

**Done when:** a stranger can clone the repo, run it locally, read the docs, and understand every table without asking me a question. **Mostly met** — everything DuckDB-based is real and verified. One thing needs an account only a person can create: logging the Evidence Studio dashboard in (`evidence login`) against a MotherDuck token — see DECISIONS.md. The GitHub Actions workflows exist (`.github/workflows/`) but haven't actually run, since this repo has no GitHub remote yet.

---

## Deliberate constraints

A few rules I'm holding myself to, because they're what the job actually demands.

**Every mart column gets a description.** Not "customer_id — the customer ID". An actual explanation of what it means and when it's null.

**Every non-obvious choice goes in `DECISIONS.md`.** Short entries. What I chose, what I rejected, why. This file matters more than the SQL.

**Business rules get tested, not just schemas.** Checking that a column is unique is easy and proves little. Checking that refunds never exceed the original order value proves I understood the domain.

**The repo must run on a laptop.** Anyone should be able to clone this and see it work in under two minutes, with no account and no credentials.

---

## Running it

```bash
uv sync
uv run python generator/generate.py --years 3
uv run python pipeline/load.py
uv run dbt build --target duckdb
uv run dbt docs generate && uv run dbt docs serve
```

Or, equivalently: `make demo`.

---

## Glossary

Terms that show up in the code, in plain words.

**Grain** — What one row of a table represents. Getting this wrong is the single most common cause of wrong numbers, which is why every fact model states it in the first comment.

**Fact table** — Records things that happened. Orders, shipments, refunds. Long and narrow, grows forever.

**Dimension table** — Describes the things involved. Customers, products, dates. Short and wide, changes slowly.

**Star schema** — Facts in the middle, dimensions around the edge, joined on keys. Named for how it looks drawn out. The point is that most business questions become one join away from an answer.

**Slowly changing dimension (Type 2)** — Keeping history when a descriptive attribute changes, instead of overwriting it. Lets you ask "what was true back then" rather than only "what is true now".

**Accumulating snapshot** — A fact table with one row per process, updated as the process moves through its stages. Good for anything with a lifecycle, like an order working its way to a doorstep.

**Incremental model** — A table that only processes new or changed rows on each run rather than rebuilding everything. Faster and much cheaper, at the cost of having to think carefully about late-arriving data.

**Staging vs marts** — Staging is cleanup with no opinions. Marts are opinions, built on clean data. Keeping them separate means you can change your mind about the business logic without re-litigating the data cleaning.

---

## Status

Stages 1 through 3 are functionally done against DuckDB: `make demo` generates, loads (twice, for real snapshot/lookback history), and builds the full warehouse — star schema, incremental facts, business-rule and distribution tests, all passing. Revenue-by-category-by-month is answerable in one `SELECT`.

Two things are configured but unproven, each blocked on an account only a person can create, not on anything left to build: the GitHub Pages publish (no GitHub remote yet), and the Evidence Studio dashboard (needs `evidence login` plus a MotherDuck token — Evidence changed products mid-project; see DECISIONS.md). Everything else runs locally with no account.
