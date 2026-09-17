"""Loads this build's precomputed JSON instead of querying DuckDB live.

Mirrors ../warehouse.py's `query()` closely enough that app.py/pages/*.py
here read almost the same as the Streamlit Community Cloud versions — the
difference is a build-time JSON file instead of a live connection.
"""

import json

import pandas as pd


def load(name: str) -> pd.DataFrame:
    with open(f"data/{name}") as f:
        return pd.DataFrame(json.load(f))
