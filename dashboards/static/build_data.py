"""Precomputes this build's data files.

Run once per CI build, right after `dbt build`, against the same
data/nordmarkt.duckdb the Streamlit Community Cloud app (../app.py) queries
live. This build can't run that query itself: it ships as a static site
where DuckDB doesn't run inside the Pyodide/WebAssembly runtime stlite uses
to run Streamlit in the browser — so the same queries run once here instead,
and the results ship as JSON. See DECISIONS.md.
"""

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import queries

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "nordmarkt.duckdb"
DATA_DIR = Path(__file__).resolve().parent / "data"

DATASETS = {
    "revenue-totals.json": queries.REVENUE_TOTALS,
    "revenue-by-month.json": queries.REVENUE_BY_MONTH,
    "revenue-by-currency.json": queries.REVENUE_BY_CURRENCY,
    "category-revenue.json": queries.CATEGORY_REVENUE,
    "category-revenue-by-month.json": queries.CATEGORY_REVENUE_BY_MONTH,
    "fulfilment-summary.json": queries.FULFILMENT_SUMMARY,
    "fulfilment-by-month.json": queries.FULFILMENT_BY_MONTH,
    "fulfilment-by-status.json": queries.FULFILMENT_BY_STATUS,
}


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        for filename, sql in DATASETS.items():
            df = con.execute(sql).df()
            for column in df.columns:
                if df[column].dtype.kind == "M":  # datetime64 -> plain ISO date string
                    df[column] = df[column].dt.strftime("%Y-%m-%d")
            (DATA_DIR / filename).write_text(df.to_json(orient="records"))
    finally:
        con.close()


if __name__ == "__main__":
    main()
