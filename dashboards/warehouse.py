"""Builds the demo warehouse once per running app instance and caches it.

Streamlit Community Cloud containers are ephemeral, and `data/nordmarkt.duckdb`
is deliberately gitignored (see the root .gitignore) since it's a build
artifact that changes on every run. So there's nothing to query when a cold
container starts — this runs the same generator -> dlt -> dbt pipeline
`make demo` runs locally, once, the first time anyone visits, then every
later visitor is served from the cached connection until the container
restarts.
"""

import os
import subprocess
import sys
from pathlib import Path

import duckdb
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "nordmarkt.duckdb"


def _run(*args: str) -> None:
    subprocess.run(
        args,
        cwd=REPO_ROOT,
        check=True,
        env={**os.environ, "DBT_PROFILES_DIR": str(REPO_ROOT)},
    )


@st.cache_resource(show_spinner="Building the demo warehouse (generator -> dlt -> dbt)...")
def _build() -> None:
    if DB_PATH.exists():
        return
    _run(sys.executable, "generator/generate.py", "--profile", "demo", "--seed", "42")
    _run(sys.executable, "pipeline/load.py", "--target", "duckdb")
    _run("dbt", "deps")
    _run("dbt", "build", "--target", "duckdb")
    # dim_customer's Type-2 history needs two real extracts to snapshot a diff
    # between — see DECISIONS.md. This simulates the second one.
    _run(sys.executable, "generator/mutate_customers.py", "--seed", "43")
    _run(sys.executable, "pipeline/load.py", "--target", "duckdb")
    _run("dbt", "build", "--target", "duckdb")


@st.cache_resource(show_spinner=False)
def _connection() -> duckdb.DuckDBPyConnection:
    _build()
    return duckdb.connect(str(DB_PATH), read_only=True)


def query(sql: str):
    return _connection().execute(sql).df()
