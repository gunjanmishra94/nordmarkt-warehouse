# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The full rationale behind these rules lives in [README.md](README.md), [STACK.md](docs/STACK.md) and [DEPLOY.md](docs/DEPLOY.md). This file is just the practices to follow when writing code — consult those for the "why" behind any rule that seems arbitrary.

## Formatting

- Formatting is handled by SQLFluff (SQL) and Ruff (Python) via pre-commit, not by hand. Don't hand-tune whitespace/quoting style that a formatter would just rewrite — run the formatter instead of eyeballing it.
- Never quote a SQL identifier and never rely on mixed case. Snowflake folds unquoted identifiers to uppercase, DuckDB preserves them as written — the only style that works on both is lowercase, unquoted, everywhere.

## Comments

- Default to no comments. Only write one when the *why* isn't obvious from the code itself — a non-obvious constraint, a cross-warehouse workaround, a deliberate tradeoff.
- Exception that's mandatory, not optional: every fact model's first lines must state its grain explicitly (what one row represents). This is a comment that always earns its place — grain confusion is the single most common source of wrong numbers here.
- Don't write comments that restate what a column or function name already says.

## dbt model conventions

- Staging models: one per source table, renaming/casting/UTC-conversion/deduplication only. No business logic, no joins. If a staging model needs a join, that logic belongs in a mart instead.
- Mart models are where business logic and joins live. Keep that separation strict so business-logic changes never require re-touching the cleaning layer.
- When DuckDB and Snowflake genuinely differ (identifier casing, `VARIANT`/`NUMBER` vs `JSON`/`DECIMAL`, `dateadd`/`datediff` argument order, incremental strategies), isolate the difference once in a macro using dbt's adapter dispatch. Never write `{% if target.type == 'snowflake' %}` inline in a model — that forces every reader to read the model twice and lets divergence spread silently.
- Always use an explicit `DECIMAL(p, s)`, never a default/implicit precision, for monetary values.
- Every column in a mart model needs a real schema.yml description: what it means and when it's null. Never a restatement of the column name (e.g. not `customer_id — the customer ID`).

## Testing conventions

- Schema tests (unique, not_null, relationships) are the floor, not the goal — they're necessary but prove almost nothing about correctness.
- Every real business rule gets a singular test asserting it directly: e.g. refunds never exceed the original order value, no delivery date before its order date, allocated shipping across order lines sums back to the amount actually charged. Write the singular test in the same PR as the logic it's guarding, not as follow-up.
- Prefer a singular test that queries for violating rows (asserting zero rows returned) over a generic test macro when the rule is domain-specific.

## Recording decisions

- Any non-obvious modelling or engineering choice goes in `DECISIONS.md` as a short entry: what was chosen, what was rejected, and why. Write the entry in the same change that makes the decision, not retroactively. Treat this file as part of the deliverable, not optional documentation.

## Python (generator) conventions

- Define data shapes with Pydantic models; treat them as the documented contract for what the raw layer should contain, not just internal validation.
- The generator's randomness must be seeded and the seed passed explicitly (not hardcoded as a default that quietly changes) — output must be reproducible run to run.

## Dependencies

- Before adding any new tool or library, check [STACK.md](docs/STACK.md)'s "deliberately not in the stack" section — most obvious additions (Docker, Airflow/Dagster, Spark, Kafka, a semantic layer) were already considered and rejected for a stated reason. Don't reintroduce one without addressing why it was rejected.
