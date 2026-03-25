"""Mutates a slice of already-generated customers to simulate a later extract.

A dbt snapshot only produces Type-2 history across *multiple* runs against a
changing source — one run just captures one version of every row. This script
is what makes `dim_customer`'s snapshot history real instead of fabricated:
run it between two `pipeline/load.py` + `dbt snapshot` cycles and a handful of
customers will genuinely have moved house or changed tier between the two.

Mutated customers always get `postal_code` set (never `zip_code`), since a
change made "today" uses whatever field the source system uses today.
"""

import argparse
import random
from pathlib import Path

import pandas as pd
from faker import Faker

COUNTRY_LOCALES = {"DE": "de_DE", "AT": "de_AT", "CH": "de_CH"}
TIERS = ["basic", "plus", "premium"]
TIER_WEIGHTS = [0.6, 0.3, 0.1]
MUTATION_RATE = 0.03


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate address/tier changes for a slice of customers."
    )
    parser.add_argument("--seed", type=int, default=43)
    parser.add_argument("--data-dir", type=Path, default=Path("data/generated"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    Faker.seed(args.seed)
    fakers = {country: Faker(locale) for country, locale in COUNTRY_LOCALES.items()}

    path = args.data_dir / "customers.parquet"
    customers = pd.read_parquet(path)

    mutate_mask = (
        customers.index.to_series().sample(frac=MUTATION_RATE, random_state=args.seed).index
    )
    changed = 0
    for idx in mutate_mask:
        fk = fakers[customers.at[idx, "country"]]
        change_address = random.random() < 0.7
        change_tier = random.random() < 0.4
        if not change_address and not change_tier:
            change_address = True

        if change_address:
            customers.at[idx, "city"] = fk.city()
            customers.at[idx, "address_line"] = fk.street_address()
            customers.at[idx, "postal_code"] = fk.postcode()
        if change_tier:
            customers.at[idx, "tier"] = random.choices(TIERS, weights=TIER_WEIGHTS)[0]
        changed += 1

    customers.to_parquet(path, index=False)
    print(f"mutated {changed:,} of {len(customers):,} customers -> {path}")


if __name__ == "__main__":
    main()
