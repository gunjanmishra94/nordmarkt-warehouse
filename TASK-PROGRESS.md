# Task Progress

Tracks what's actually been built against README.md's three-stage plan. Update this as stages progress; it's a working log, not part of the portfolio narrative.

---

## Stage 1 — Foundations

**Status: done.**

- [x] Repo/dbt scaffolding: `dbt_project.yml`, `profiles.yml`, folder structure (`generator/`, `pipeline/`, `models/staging/`, `macros/`)
- [x] `duckdb` target configured and proven in `profiles.yml`. (Snowflake was dropped as a target — see DECISIONS.md — so there's no second target left to prove.)
- [x] Data generator (`generator/generate.py`, `generator/schemas.py`) — customers, products, orders, order lines, shipments, refunds; seeded and deterministic
- [x] Deliberate mess: duplicate order IDs, late-arriving shipment/refund events, mixed timezones (Berlin/Zurich/UTC), mid-history `zip_code` → `postal_code` rename
- [x] dlt load (`pipeline/load.py`) into DuckDB, plus daily EUR/CHF rates from the Frankfurter API
- [x] Staging layer: 7 models in `models/staging/`, one per source, deduped, UTC-converted via the `to_utc_timestamp` macro, no business logic
- [x] Basic tests: unique/not_null on primary keys, `relationships` on every foreign key
- [x] SQLFluff + pre-commit wired up and passing

**Verified:** `uv sync && make demo` runs clean from a fresh tree with no pre-set env vars; `dbt build --target duckdb` passes 31/31 (7 models + 24 tests); same-seed reruns produce identical row counts.

---

## Stage 2 — The star schema

**Status: done.**

- [x] `dim_date`, including German public holidays by federal state — via `dbt_utils.date_spine` + a computed seed (`scripts/generate_de_holidays.py` → `seeds/de_public_holidays.csv`); holiday detail kept in a separate `dim_public_holiday_de` so `dim_date` stays one row per day
- [x] `dim_product`, with a derived `price_band`
- [x] `dim_customer` as a **real** dbt snapshot (`snapshots/dim_customer_snapshot.sql`, `strategy: check`) — `generator/mutate_customers.py` mutates ~3% of customers between two `make demo` build passes so the snapshot captures a genuine diff, not a fabricated one
- [x] `fct_order_lines`, grain stated explicitly, shipping/discount allocated proportionally across lines
- [x] Two singular tests proving the allocation sums back to the order-level amount (`tests/assert_shipping_allocation_sums_correctly.sql`, `tests/assert_discount_allocation_sums_correctly.sql`)
- [x] Shipping/discount (captured in local currency) converted to EUR using the FX rate on the order's date, via the `to_eur` macro
- [x] Column-level descriptions for every mart field (`models/marts/_marts.yml`)
- [x] `DECISIONS.md` started — 5 entries so far

**Verified:** clean-tree `uv sync && make demo` runs both build passes (57/57 each); at least 147 customers have genuine 2-version snapshot history with correct `valid_from`/`valid_to`; the actual done-when query (revenue by category by month, in EUR, one `SELECT`) returns correct numbers; `pre-commit run --all-files` passes.

**New generator fields this stage needed** (not anticipated in Stage 1): `Order.shipping_amount_local` and `Order.discount_amount_local` — see DECISIONS.md for why they're in local currency, not EUR.

---

## Stage 3 — Make it real

**Status: done against DuckDB.** Two items blocked on external accounts, not on remaining build work. Snowflake was dropped as a target this stage — see DECISIONS.md — so the credit-cost/warehouse-sizing/`ACCOUNT_USAGE` line that used to be pending here is gone rather than pending.

- [x] `fct_order_lines` converted to incremental (`delete+insert`, trailing lookback window on `order_date_utc`)
- [x] `fct_order_fulfilment` as an accumulating snapshot (placed → shipped → delivered → refunded; no "picked" stage — see DECISIONS.md), incremental with a lookback on `recorded_at`
- [x] `macros/backfill_incremental_model.sql` — generic backfill for either incremental model
- [x] Business-rule singular tests: `assert_refunds_never_exceed_order_value`, `assert_no_delivery_before_order_date`, `assert_no_negative_quantities`
- [x] `dbt_expectations` distribution tests on `fct_order_lines` and a new `agg_daily_revenue` (row count + value bounds; a sanity check, not anomaly detection — see DECISIONS.md)
- [x] README "What the numbers mean" section
- [x] `DECISIONS.md` — new entries this stage (lookback/backfill design, no-picked-stage, dbt_expectations scope, the Evidence pivot, dropping Snowflake)
- [ ] Publish dbt docs to GitHub Pages — workflow files exist (`.github/workflows/demo.yml`, `ci.yml`, `.devcontainer/devcontainer.json`) but have never run; no GitHub remote yet
- [~] Three Evidence pages (revenue overview, category trends, fulfilment timing) — written in `dashboards/pages/`, real current Markdoc syntax confirmed via `evidence docs component` (no login needed for that), and `evidence validate` passes. **Not verified live**: Evidence pivoted from a static/no-login tool to "Evidence Studio" mid-project, which needs `evidence login` + a MotherDuck connection (`dashboards/connection.example.yaml`) neither of which can be completed without a person's credentials. See DECISIONS.md.

**Verified:** clean-tree `make demo` builds both passes green (72/72 checks each); manually inserted a genuinely late-arriving shipment (recorded_at past the existing watermark) and confirmed a plain `dbt run --select fct_order_fulfilment` (no `--full-refresh`) picked it up; exercised the backfill macro end-to-end (delete a window, confirm empty, reprocess with a widened lookback, confirm restored).

**Also fixed along the way:** `docs/DEPLOY.md`'s entire "how the public demo works" section and its documented Makefile block predated Evidence's pivot and described a deployment model that no longer exists — rewritten to match reality (dbt docs only on our GitHub Pages site; the dashboard publishes itself via Evidence Studio once connected).
