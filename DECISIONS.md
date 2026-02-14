# Decisions

Short entries: what was chosen, what was rejected, and why. Added to in the same change that makes the decision — see CLAUDE.md.

---

## `fct_order_lines` is at order-line grain, not order grain

**Chosen:** one row per product within an order.

**Rejected:** one row per order, with line items nested or pre-aggregated.

**Why:** analysing by product category needs one row per product. The cost is that order-level values (shipping, discount) would be triple-counted if summed naively across lines of a multi-line order — handled by allocating them proportionally across lines instead, with `tests/assert_shipping_allocation_sums_correctly.sql` and `tests/assert_discount_allocation_sums_correctly.sql` proving the allocation adds back up to what was actually charged.

---

## Shipping and discount are captured in the order's local currency, converted to EUR at allocation time

**Chosen:** `Order.shipping_amount_local` / `discount_amount_local` are in the order's own currency (EUR or CHF), picked from realistic flat checkout values independent of any FX rate. `fct_order_lines` converts them to EUR using `stg_fx_rates` (the rate on the order's date) before allocating across lines.

**Rejected:** generating these already in EUR, or deriving them from the FX rate at generation time.

**Why:** this is what a real checkout actually records (a local flat fee/discount, not an FX-derived one), and it gives the "convert to EUR using the rate on the order date" requirement something genuine to do. Product catalog prices (`unit_price_eur`) stay canonically EUR throughout — a multi-currency retailer keeping its catalog in one base currency internally is normal, and having only one EUR-denominated price avoids a second, redundant conversion path.

---

## `dim_customer`'s Type-2 history comes from a real dbt snapshot, not a synthesized one

**Chosen:** `snapshots/dim_customer_snapshot.sql` snapshots `stg_customers` with `strategy: check` over address/tier columns. `generator/mutate_customers.py` mutates ~3% of customers between two `make demo` build passes, so the snapshot table captures a genuine diff.

**Rejected:** building an SCD2-shaped mart directly from a single-shot "current state" extract (e.g. faking `valid_from`/`valid_to` with window functions), which would have been far simpler.

**Why:** README explicitly calls for `dim_customer` "as a dbt snapshot" — the point is to demonstrate the actual dbt snapshot mechanism, which only produces real history across multiple runs against a changing source. A demo dataset generated once has nothing to diff, so the mutation step exists purely to give the snapshot a second, different extract to compare against. The cost is `make demo` now runs `dbt build` twice; that's the price of the history being real.

---

## `dim_date` stays one row per day; holiday detail lives in a separate `dim_public_holiday_de`

**Chosen:** `dim_date` (via `dbt_utils.date_spine`) is one row per calendar day, with a simple `is_public_holiday_de` flag and a states-observing count. Full per-state detail lives in `dim_public_holiday_de`, grain `holiday_date` x `federal_state`, sourced from the committed seed `seeds/de_public_holidays.csv`.

**Rejected:** exploding `dim_date` itself to a `date` x `federal_state` grain (16x the rows) so every row could carry state-specific holiday flags.

**Why:** a date dimension needs to stay one-row-per-day to be joinable to facts without introducing a fan-out. The federal-state detail README asks for still exists and is queryable, just in its own table.

**Known simplifications in the holiday data** (`scripts/generate_de_holidays.py`): Mariä Himmelfahrt is legally a municipality-level holiday in majority-Catholic parts of Bayern, treated here as statewide for all of Bayern and Saarland. Frauentag (Berlin, Mecklenburg-Vorpommern) and Weltkindertag (Thüringen) are applied across the whole 2015–2031 range rather than from their actual introduction years (2019/2023/2019 respectively). None of this affects the demo data meaningfully; it would matter if this table were ever used for real payroll/logistics calculations.

---

## `dim_product.price_band` thresholds

**Chosen:** budget < €25, mid < €100, premium ≥ €100.

**Why:** a simple, fixed cut rather than a percentile-based or category-relative banding. Good enough for a homeware catalog at this scale; would need revisiting if the product mix changed substantially.

---

## Incremental models reprocess a trailing lookback window, not "just what's new"

**Chosen:** `fct_order_lines` and `fct_order_fulfilment` are both `materialized='incremental'` with `incremental_strategy='delete+insert'`. On every run they recompute a trailing window (`var('late_arrival_lookback_days', 7)`) rather than only rows created since the last run. `fct_order_lines` anchors the window on `order_date_utc`; `fct_order_fulfilment` anchors on `recorded_at` (when shipment/refund events were recorded, via a `greatest()` across every stage), because that's the field that can genuinely trail behind when something happened.

**Rejected:** `incremental_strategy='merge'` (not portable — dbt-duckdb's merge support and Snowflake's differ in ways not worth tracking down for this project), and a naive "only rows newer than max(loaded_at)" filter, which would never catch a shipment recorded late for an old order.

**Why:** this is verified, not assumed — see the manual test in this session: an order with no shipment got one inserted with `recorded_at` past the table's existing watermark, and a plain `dbt run --select fct_order_fulfilment` (no `--full-refresh`) picked it up correctly. `macros/backfill_incremental_model.sql` exists for the rarer case of fixing a window further back than the lookback reaches — it deletes the window, but the model's own filter is still anchored at `max(date_column) - lookback_days`, so reprocessing an old window needs `--vars` widened enough to reach it (e.g. days-since-today), not just the delete.

---

## `fct_order_fulfilment` has no "picked" stage

**Chosen:** tracks placed → shipped → delivered → refunded.

**Why:** the generator only ever produces orders, shipments (status shipped/delivered) and refunds — never a distinct "picked" event. Adding one would mean extending the generator for a stage nothing downstream currently needs; the four stages tracked are the ones we actually have data for.

---

## `dbt_expectations` here is a sanity bound, not anomaly detection

**Chosen:** `expect_table_row_count_to_be_between` on `fct_order_lines`, `expect_column_values_to_be_between` on quantity/net_revenue_eur, and the same on a small aggregate model (`agg_daily_revenue`) built solely to give a distribution test something to check.

**Rejected:** trying to detect "today's revenue is 3x a normal day" as a relative, rolling-average anomaly.

**Why:** true day-over-day anomaly detection needs a baseline and is explicitly a later-project concern per docs/STACK.md ("Elementary for freshness and anomaly monitoring"). Static bounds here catch the same class of gross error the README's example describes (a silent multiplication or a broken join) without pretending to be a monitoring system.

---

## The dashboard runs on Evidence Studio + MotherDuck, not the static Evidence docs/STACK.md originally chose

**Chosen:** `dashboards/` is an Evidence Studio project connecting to MotherDuck (hosted DuckDB) as a "direct connector." `pipeline/load.py --target motherduck` and `profiles.yml`'s `motherduck` target let the same dbt project build there.

**Rejected:** the original static, no-login, DuckDB-in-browser design — it's no longer available. Also rejected: pinning an old, unmaintained Evidence version just to keep that design; and switching to a different dashboard tool entirely.

**Why:** Evidence pivoted from a static site generator to a hosted product ("Evidence Studio") between when docs/STACK.md was written and this stage. Confirmed directly from their repo (`evidence-dev/evidence`, `docs/migration-guide.mdx`): the old static/WASM/no-login mode is explicitly named "Legacy Evidence" and deprecated. Studio requires `evidence login` and exactly one live server-side "direct connector" — the supported list is BigQuery, ClickHouse, Cube, Databricks, Fabric, MotherDuck, Postgres, Snowflake. No local-file DuckDB connector exists. MotherDuck is the only DuckDB-family option, so it's the one that keeps the rest of this project's story (dbt/dlt targeting the same warehouse family, free tier, no company account) mostly intact.

**What this costs:** both MotherDuck and Evidence Studio need their own account/token — genuinely new external dependencies this project didn't have before, in the same "configured but can't be proven without an account" bucket Snowflake used to occupy (Snowflake itself was later dropped — see below). Unlike Snowflake, an actual login (`evidence login`, browser-based) is required even to view the dashboard locally — there's no equivalent to `dbt build --target duckdb` that stays entirely offline. The three dashboard pages (`dashboards/pages/*.md`) were written against the real, current Markdoc component syntax (checked via `evidence docs component <name>`, which works without logging in) rather than guessed, but the table addressing (`main.<table>`, matching our dbt schema) is inferred from the MotherDuck connector docs, not verified against a live connection.

**Superseded:** see the entry below — Evidence Studio turned out not to have the free tier this decision assumed, and both it and MotherDuck were dropped.

---

## Dropped Evidence Studio and MotherDuck; the dashboard is now a Streamlit app that queries DuckDB directly

**Chosen:** `dashboards/` is a three-page Streamlit app (`app.py` plus `pages/`) that opens `data/nordmarkt.duckdb` directly with the `duckdb` Python package — no hosted warehouse connector in the loop at all. Since that file is gitignored (a build artifact, not something committed), `warehouse.py` runs the same generator → dlt → dbt pipeline `make demo` runs locally the first time any page is opened in a fresh container, caches the result for the container's lifetime, and every later visitor is served from that cached connection. Deployed on Streamlit Community Cloud, which needs its own account but is a genuine, permanent free tier (1 GB RAM, a handful of concurrent users, sleeps after inactivity) rather than a trial.

**Rejected:** staying on Evidence Studio (see the entry above); Observable Framework, a static-site generator that was actually built out first (data loaders querying DuckDB at CI build time, output riding on the existing GitHub Pages site, zero new accounts) before being dropped in favor of a Python-native dashboard instead of adding an npm/JS toolchain to an otherwise all-Python project.

**Why:** the previous entry's premise was wrong. Checked directly against evidence.dev/pricing while setting the MotherDuck connection up: Evidence Studio has no permanent free tier — a 30-day trial, then $2,500/month (Team plan) or custom Enterprise pricing. That directly breaks this project's guiding constraint (docs/DEPLOY.md: "the permanent demo cannot depend on an account only I have," hosting should stay near €0). Once Evidence was out, MotherDuck went with it — it existed solely to give Evidence Studio a live server-side connection (see docs/STACK.md), and a Python dashboard has no need for a hosted warehouse when it can just open the DuckDB file itself.

**What this costs:** the fully static, account-free story the Observable Framework build briefly had is gone — Streamlit needs its own account on Streamlit Community Cloud, same as Evidence Studio did, just without the trial trap. The real new cost is the cold-start rebuild: the first visitor after the container's been asleep waits tens of seconds for the warehouse to rebuild, rather than getting an instant static page. Accepted because a Python-native dashboard fits the rest of this all-Python-except-SQL project better than either alternative, and "occasionally slow" beats "eventually $2,500/month."

**What this removes:** `profiles.yml`'s `motherduck` target, the `MOTHERDUCK_TOKEN`/`MOTHERDUCK_DATABASE` env vars, `pipeline/load.py --target motherduck`, and the `motherduck` extra on the `dlt` dependency. DuckDB-only, for real this time — the dashboard doesn't change that, since it's still the same single local file everything else in this project builds and reads.

**Update:** the account-free option didn't have to be gone for good — see the next entry.

---

## Added a second, static dashboard build (`dashboards/static/`) alongside the live one, using stlite

**Chosen:** a second build of the same three pages, `dashboards/static/`, using [stlite](https://github.com/whitphx/stlite) — it runs the real Streamlit package inside a Pyodide (WebAssembly) Python runtime in the browser, so the output is a plain static HTML/JS bundle. `.github/workflows/demo.yml` runs `dashboards/static/build_data.py` right after `dbt build` (the same `queries.py` SQL the live app uses, run once against `data/nordmarkt.duckdb`, dumped to JSON), then copies `dashboards/static/` into the site published to GitHub Pages at `/dashboard/`. Both dashboard builds now exist side by side; neither replaced the other.

**Rejected:** dropping the live Streamlit Community Cloud version in favor of the static one — the static build is a snapshot from the last CI run, not a live queryable connection, so it's a genuine tradeoff rather than a strict upgrade. Also rejected: reviving Observable Framework for this instead, since the point was to keep the dashboard in Streamlit/Python.

**Why:** the live version's real remaining cost was needing its own Streamlit Community Cloud account at all, on top of the cold-start rebuild — the thing the original Evidence pick was supposed to avoid. stlite closes that gap for anyone who doesn't need live querying: no account, no server, rides on the GitHub Pages build the dbt docs site already uses.

**What this costs:** a real download of Pyodide + pandas + Streamlit in the visitor's browser before anything renders (tens of MB, cached after first load) — slower first paint than either a live server or the dbt docs' plain static HTML. Verified end-to-end with a real, headless Chromium browser (Playwright) during development, not just by reading stlite's docs: all three pages render with the correct numbers. One caught-and-fixed bug along the way — `st.dataframe(..., width="stretch")` throws `TypeError: 'str' object cannot be interpreted as an integer` on the Streamlit version stlite currently bundles (1.40.1); switched to `use_container_width=True` in `static/` only, since Streamlit Cloud's newer version handles `width="stretch"` fine. One accepted, unfixed cosmetic issue: every chart logs a harmless `Infinite extent` warning to the browser console (an Altair/Vega-Lite quirk in that same bundled version) with no visible effect on what's rendered.

---

## MotherDuck comes back, this time only to give the live Streamlit Cloud app a warm database

**Chosen:** `profiles.yml` gets a `motherduck` dbt target (`path: "md:{database}?motherduck_token={token}"`), `pipeline/load.py --target motherduck` loads into it via dlt's native MotherDuck destination, and `.github/workflows/motherduck.yml` runs the same generate → load → dbt-build-twice sequence `demo.yml` runs, nightly and on push to `main`, against MotherDuck instead of the local file. `dashboards/warehouse.py` now checks for `MOTHERDUCK_TOKEN`: set (the Streamlit Community Cloud deploy) it connects straight to MotherDuck and queries it live; unset (local `make dashboard`) it builds and queries `data/nordmarkt.duckdb` exactly as before.

**Rejected:** rebuilding the whole warehouse in-process on every cold start (the status quo this replaces for the live deploy only), and re-adopting MotherDuck for local development or for the static/CI-built dashboard — neither of those needed it and both stay exactly as they were.

**Why:** this is a different problem than the one that got MotherDuck dropped before. Last time (see above) it existed solely because Evidence Studio required a live server-side connector; once Evidence Studio was dropped for having no free tier, MotherDuck had no remaining reason to exist, since a Python dashboard could just open the DuckDB file itself. That reasoning held right up until the file stopped being something you could "just open" for a deployed app: Streamlit Community Cloud containers are ephemeral, so every cold start after a sleep paid a tens-of-seconds full pipeline rebuild before the first page could render. MotherDuck removes that by giving the live deploy an always-there database a scheduled job keeps fresh, instead of the app rebuilding it on demand.

**What this costs:** a MotherDuck account/token, which is a real new external dependency — but it's additive to a cost the live deploy already had (Streamlit Community Cloud's own account), not a new category of "account only I have" the way it would be for the account-free paths. `docs/DEPLOY.md`'s constraint — the *permanent* demo can't depend on an account only I have — still holds: the GitHub Pages docs site and the stlite static dashboard remain fully account-free and untouched by this change. Only the live, already-account-gated Streamlit deploy points at MotherDuck.

---

## Snowflake dropped as a target; DuckDB only

**Chosen:** the project targets DuckDB exclusively. The `snowflake` output in `profiles.yml`, the `SNOWFLAKE_*` env vars, the `dbt-snowflake` and `dlt[snowflake]` dependencies, the `make snowflake` / `pipeline/load.py --target snowflake` paths, and the `snowflake__` variants of the `date_diff_hours`, `iso_day_of_week` and `to_utc_timestamp` adapter-dispatch macros are all removed. Those macros are now plain single-adapter macros — there's no second dialect left to isolate a difference from.

**Rejected:** keeping Snowflake configured-but-unproven indefinitely (the state it had been in since Stage 1), and getting an actual Snowflake trial account to prove it.

**Why:** every "prove it on Snowflake" line item across README.md/TASK-PROGRESS.md had sat unchecked since Stage 1 for the same reason: a 30-day trial that nobody had started, because starting it commits to either a live spend or a dead, unproven target once it lapses. Carrying the second-adapter machinery (a config target, dependency, and three macro variants) for a warehouse that was never actually exercised was pure speculative work — dbt's adapter-dispatch pattern is worth demonstrating, but only with a second adapter genuinely in play, not as a placeholder. If Snowflake experience needs demonstrating later, it belongs in a project scoped and funded around Snowflake-only concerns from the start (see docs/STACK.md's "Deliberately not in the stack"), not carried here as unproven config.

**What this doesn't change:** at the time, MotherDuck stayed, because it was the same DuckDB engine/adapter (needed only because Evidence Studio required a live server-side connection — see the entries above). MotherDuck was itself dropped later, once Evidence Studio was — see the dashboard entries above.

---

## Fixed: `hours_shipped_to_delivered` was silently always zero

**Chosen:** `generator/generate.py`'s `build_shipments()` now emits two shipment events for a delivered order — a `shipped` event, then a `delivered` event 1-5 days later — instead of one. Added `tests/assert_delivery_takes_positive_time.sql`, asserting `delivered_at > shipped_at` for every delivered order.

**Rejected:** leaving it as a known quirk of the demo data, or "fixing" it only in the dbt model.

**Why:** the generator only ever wrote one shipment row per order — status `shipped` or `delivered` depending on the order's final state, both timestamped identically. `fct_order_fulfilment`'s `shipped` CTE (`status in ('shipped', 'delivered')`) and `delivered` CTE (`status = 'delivered'`) then both picked up that same single row for any delivered order, so `shipped_at` and `delivered_at` were always the same timestamp. `hours_shipped_to_delivered` — a column the README's "What the numbers mean" section documents as real — was therefore exactly `0` for all 10,000+ delivered orders, and nothing caught it: it's a valid number, just always the same wrong one, which is precisely the class of error a `not_null`/`unique` test can't see and `dbt_expectations`' static bounds didn't happen to cover either. Caught only because someone looked at the actual rendered dashboard number and it looked implausible. `stg_shipments` had already documented the intended grain as "the pick/ship/deliver events" (plural) per order — the generator just never lived up to its own model's assumption.

**What this proves, and what it doesn't:** this is the exact failure mode `CLAUDE.md`'s testing conventions warn about — "Every real business rule gets a singular test asserting it directly," precisely because schema tests "prove almost nothing about correctness." One existed for the adjacent rule (`assert_no_delivery_before_order_date.sql`, checking `delivered_at >= placed_at`) but wouldn't have caught this, since `delivered_at == shipped_at` doesn't violate "not before the order was placed." The new test specifically asserts a *positive* gap, which this bug would have failed.
