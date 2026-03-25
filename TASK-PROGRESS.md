# Task Progress

Tracks what's actually been built against README.md's three-stage plan. Update this as stages progress; it's a working log, not part of the portfolio narrative.

---

## Stage 1 — Foundations

**Status: done**, except the one item that structurally can't be finished yet.

- [x] Repo/dbt scaffolding: `dbt_project.yml`, `profiles.yml`, folder structure (`generator/`, `pipeline/`, `models/staging/`, `macros/`)
- [ ] Two targets configured **and proven** — `duckdb` and `snowflake` are both configured in `profiles.yml` and `.env.example`, but only `duckdb` has actually been run. No Snowflake trial account exists yet.
- [x] Data generator (`generator/generate.py`, `generator/schemas.py`) — customers, products, orders, order lines, shipments, refunds; seeded and deterministic
- [x] Deliberate mess: duplicate order IDs, late-arriving shipment/refund events, mixed timezones (Berlin/Zurich/UTC), mid-history `zip_code` → `postal_code` rename
- [x] dlt load (`pipeline/load.py`) into DuckDB, plus daily EUR/CHF rates from the Frankfurter API
- [x] Staging layer: 7 models in `models/staging/`, one per source, deduped, UTC-converted via the `to_utc_timestamp` macro, no business logic
- [x] Basic tests: unique/not_null on primary keys, `relationships` on every foreign key
- [x] SQLFluff + pre-commit wired up and passing

**Verified:** `uv sync && make demo` runs clean from a fresh tree with no pre-set env vars; `dbt build --target duckdb` passes 31/31 (7 models + 24 tests); same-seed reruns produce identical row counts.

**Pending:** get a Snowflake trial account and run `make snowflake` to actually prove the second target, not just configure it.

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

**Status: not started.**

- [ ] `fct_order_lines` converted to incremental, with a late-arrival lookback window and backfill macro
- [ ] `fct_order_fulfilment` as an accumulating snapshot
- [ ] Business-rule singular tests (refunds ≤ order value, no delivery before order date, no negative quantities)
- [ ] `dbt_expectations` distribution tests
- [ ] Snowflake run: credit cost, warehouse sizing, clustering keys, `ACCOUNT_USAGE` cost attribution (depends on Stage 1's Snowflake gap being closed first)
- [ ] Publish dbt docs + dashboard to GitHub Pages per docs/DEPLOY.md
- [ ] Three Evidence pages: revenue overview, category trends, fulfilment timing
- [ ] README section explaining what the numbers mean
