.PHONY: demo generate load build docs full snowflake clean

export DBT_PROFILES_DIR := .

demo: generate load build

generate:
	uv run python generator/generate.py --profile demo --seed 42

load:
	uv run python pipeline/load.py --target duckdb

build:
	uv run dbt build --target duckdb

docs:
	uv run dbt docs generate --target duckdb && uv run dbt docs serve

full:
	uv run python generator/generate.py --profile full --seed 42

snowflake:
	uv run python pipeline/load.py --target snowflake && uv run dbt build --target snowflake

clean:
	rm -rf target dbt_packages data/generated data/*.duckdb*
