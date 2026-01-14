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

**Status: not started.**

- [ ] `dim_date`, including German public holidays by federal state
- [ ] `dim_product`
- [ ] `dim_customer` as a dbt snapshot (Type 2 SCD over address/tier changes)
- [ ] `fct_order_lines`, grain stated explicitly, shipping/discount allocation across lines + a test that the allocation sums back correctly
- [ ] Convert to EUR using the FX rate on the order date (data is already loaded via `stg_fx_rates`; not yet used anywhere)
- [ ] Column-level descriptions for every mart field
- [ ] Start `DECISIONS.md`

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
