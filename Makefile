.PHONY: demo generate deps load snapshot mutate build docs dashboard full clean load-motherduck build-motherduck demo-motherduck

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

dashboard:
	cd dashboards && uv run --with-requirements requirements.txt streamlit run app.py

load-motherduck:
	uv run python pipeline/load.py --target motherduck

build-motherduck:
	uv run dbt build --target motherduck

# Pushes a fresh demo build to MotherDuck, for the live Streamlit Cloud
# dashboard to query. Needs MOTHERDUCK_TOKEN in the environment; this is
# what .github/workflows/motherduck.yml runs on a schedule, not something
# the dashboard itself triggers.
demo-motherduck: generate deps
	$(MAKE) load-motherduck
	$(MAKE) build-motherduck
	$(MAKE) mutate
	$(MAKE) load-motherduck
	$(MAKE) build-motherduck

full:
	uv run python generator/generate.py --profile full --seed 42

clean:
	rm -rf target dbt_packages data/generated data/*.duckdb*
