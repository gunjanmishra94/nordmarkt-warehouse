.PHONY: demo generate deps load snapshot mutate build docs full clean

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

clean:
	rm -rf target dbt_packages data/generated data/*.duckdb*
