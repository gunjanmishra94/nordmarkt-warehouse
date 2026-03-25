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
