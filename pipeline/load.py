"""Loads the generator's Parquet output into the warehouse, untouched.

Also pulls real daily EUR/CHF rates from the free, keyless Frankfurter API,
covering the date range the generator actually produced, so the currency
conversion done in later stages isn't fake.
"""

import argparse
import os
from pathlib import Path

import dlt
import pandas as pd
import requests

FX_API_URL = "https://api.frankfurter.dev/v1/{start}..{end}"


def _records(path: Path) -> list[dict]:
    return pd.read_parquet(path).to_dict(orient="records")


@dlt.resource(name="customers", write_disposition="replace")
def customers_resource(data_dir: Path):
    yield _records(data_dir / "customers.parquet")


@dlt.resource(name="products", write_disposition="replace")
def products_resource(data_dir: Path):
    yield _records(data_dir / "products.parquet")


@dlt.resource(name="orders", write_disposition="replace")
def orders_resource(data_dir: Path):
    yield _records(data_dir / "orders.parquet")


@dlt.resource(name="order_lines", write_disposition="replace")
def order_lines_resource(data_dir: Path):
    yield _records(data_dir / "order_lines.parquet")


@dlt.resource(name="shipments", write_disposition="replace")
def shipments_resource(data_dir: Path):
    yield _records(data_dir / "shipments.parquet")


@dlt.resource(name="refunds", write_disposition="replace")
def refunds_resource(data_dir: Path):
    yield _records(data_dir / "refunds.parquet")


@dlt.resource(name="fx_rates", write_disposition="replace")
def fx_rates_resource(start_date: str, end_date: str):
    response = requests.get(
        FX_API_URL.format(start=start_date, end=end_date),
        params={"base": "EUR", "symbols": "CHF"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    for rate_date, rates in payload["rates"].items():
        yield {
            "rate_date": rate_date,
            "base_currency": "EUR",
            "quote_currency": "CHF",
            "rate": rates["CHF"],
        }


def build_destination(target: str):
    if target == "duckdb":
        return dlt.destinations.duckdb("data/kiezkauf.duckdb")
    if target == "snowflake":
        return dlt.destinations.snowflake(
            credentials={
                "database": os.environ["SNOWFLAKE_DATABASE"],
                "username": os.environ["SNOWFLAKE_USER"],
                "host": os.environ["SNOWFLAKE_ACCOUNT"],
                "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "WH_XS"),
                "role": os.environ.get("SNOWFLAKE_ROLE", "TRANSFORMER"),
                "private_key": Path(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"])
                .expanduser()
                .read_text(),
            }
        )
    raise ValueError(f"Unknown target: {target}")


def fx_date_range(data_dir: Path) -> tuple[str, str]:
    order_dates = pd.to_datetime(
        pd.read_parquet(data_dir / "orders.parquet")["order_date"], utc=True
    )
    return order_dates.min().date().isoformat(), order_dates.max().date().isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load generated Kiezkauf data into the warehouse.")
    parser.add_argument("--target", choices=["duckdb", "snowflake"], default="duckdb")
    parser.add_argument("--data-dir", type=Path, default=Path("data/generated"))
    args = parser.parse_args()

    pipeline = dlt.pipeline(
        pipeline_name="kiezkauf",
        destination=build_destination(args.target),
        dataset_name="raw",
    )

    start_date, end_date = fx_date_range(args.data_dir)

    info = pipeline.run(
        [
            customers_resource(args.data_dir),
            products_resource(args.data_dir),
            orders_resource(args.data_dir),
            order_lines_resource(args.data_dir),
            shipments_resource(args.data_dir),
            refunds_resource(args.data_dir),
            fx_rates_resource(start_date, end_date),
        ]
    )
    print(info)


if __name__ == "__main__":
    main()
