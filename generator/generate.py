"""Invents Nordmarkt's operational history and writes it to Parquet.

Deliberately messy, on purpose (see README.md "How it fits together"):

- a handful of orders are emitted twice under the same order_id
- shipment/refund events can be recorded days after they actually happened
- orders, shipments and refunds are timestamped in three different timezones
  (Europe/Berlin, Europe/Zurich, UTC) and never normalized here
- customers signed up before a fixed cutover date only have `zip_code` set;
  customers after it only have `postal_code` set

None of that gets cleaned up until the staging layer.
"""

import argparse
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from faker import Faker

from generator.schemas import Customer, Order, OrderLine, Product, Refund, Shipment

BERLIN = ZoneInfo("Europe/Berlin")
ZURICH = ZoneInfo("Europe/Zurich")
UTC = ZoneInfo("UTC")

PROFILES = {
    "demo": {"customers": 5_000, "products": 500, "orders": 15_000},
    "full": {"customers": 50_000, "products": 2_000, "orders": 150_000},
}

COUNTRY_WEIGHTS = {"DE": 0.6, "AT": 0.15, "CH": 0.25}
COUNTRY_LOCALES = {"DE": "de_DE", "AT": "de_AT", "CH": "de_CH"}
TIERS = ["basic", "plus", "premium"]
TIER_WEIGHTS = [0.6, 0.3, 0.1]
CATEGORIES = [
    "Kitchen",
    "Living Room",
    "Bedroom",
    "Bathroom",
    "Garden",
    "Lighting",
    "Storage",
    "Decor",
]
SUPPLIERS = [f"Supplier {letter}" for letter in "ABCDEFGH"]
ORDER_STATUSES = ["placed", "shipped", "delivered", "cancelled", "refunded"]
ORDER_STATUS_WEIGHTS = [0.05, 0.1, 0.7, 0.1, 0.05]
CARRIERS = ["DHL", "DPD", "Hermes", "GLS"]
REFUND_REASONS = ["damaged", "wrong_item", "changed_mind", "late_delivery"]

DUPLICATE_ORDER_RATE = 0.005
LATE_ARRIVAL_RATE = 0.15
REFUND_ELIGIBLE_STATUSES = {"cancelled", "refunded"}
# ORDER_STATUS_WEIGHTS gives these statuses 15% of orders combined; this rate
# is relative to that eligible pool, so refunds end up on ~5% of all orders.
REFUND_RATE_AMONG_ELIGIBLE = 0.05 / 0.15

# Flat rates as they'd actually be published at checkout in each currency, not
# derived from an FX rate — that's what makes converting them to EUR later
# (using the rate on the order's date) a real conversion instead of a no-op.
SHIPPING_OPTIONS = {
    "EUR": [0.0, 3.99, 4.99, 6.99],
    "CHF": [0.0, 4.5, 5.9, 7.9],
}
SHIPPING_WEIGHTS = [0.2, 0.3, 0.35, 0.15]
DISCOUNT_RATE = 0.2
DISCOUNT_RANGE = {
    "EUR": (5.0, 20.0),
    "CHF": (5.0, 22.0),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Nordmarkt's messy operational history.")
    parser.add_argument("--years", type=int, default=3)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="demo")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data/generated"))
    return parser.parse_args()


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def at_midnight(day: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=tz)


def random_datetime(start: date, end: date, tz: ZoneInfo) -> datetime:
    dt = at_midnight(random_date(start, end), tz)
    return dt + timedelta(seconds=random.randint(0, 86_399))


def maybe_delay(occurred_at: datetime) -> datetime:
    if random.random() < LATE_ARRIVAL_RATE:
        return occurred_at + timedelta(days=random.randint(1, 5), hours=random.randint(0, 23))
    return occurred_at


def build_customers(n: int, start: date, end: date, cutover: date) -> list[Customer]:
    fakers = {country: Faker(locale) for country, locale in COUNTRY_LOCALES.items()}
    countries = list(COUNTRY_WEIGHTS)
    weights = list(COUNTRY_WEIGHTS.values())

    customers = []
    for i in range(1, n + 1):
        country = random.choices(countries, weights=weights)[0]
        fk = fakers[country]
        signup = random_date(start, end)
        legacy = signup < cutover
        customers.append(
            Customer(
                customer_id=f"CUST-{i:06d}",
                first_name=fk.first_name(),
                last_name=fk.last_name(),
                email=fk.email(),
                country=country,
                city=fk.city(),
                address_line=fk.street_address(),
                zip_code=fk.postcode() if legacy else None,
                postal_code=None if legacy else fk.postcode(),
                tier=random.choices(TIERS, weights=TIER_WEIGHTS)[0],
                signup_date=signup.isoformat(),
                created_at=at_midnight(signup, BERLIN).isoformat(),
            )
        )
    return customers


def build_products(n: int, start: date, end: date) -> list[Product]:
    fk = Faker("de_DE")
    products = []
    for i in range(1, n + 1):
        products.append(
            Product(
                product_id=f"PROD-{i:06d}",
                name=f"{fk.word().capitalize()} {random.choice(CATEGORIES)}",
                category=random.choice(CATEGORIES),
                supplier=random.choice(SUPPLIERS),
                price_eur=round(random.uniform(5, 500), 2),
                created_at=random_datetime(start, end, BERLIN).isoformat(),
            )
        )
    return products


def build_orders(n: int, customers: list[Customer], start: date, end: date) -> list[Order]:
    orders = []
    for i in range(1, n + 1):
        customer = random.choice(customers)
        currency = "CHF" if customer.country == "CH" else "EUR"
        discount = 0.0
        if random.random() < DISCOUNT_RATE:
            discount = round(random.uniform(*DISCOUNT_RANGE[currency]), 2)
        orders.append(
            Order(
                order_id=f"ORD-{i:07d}",
                customer_id=customer.customer_id,
                order_date=random_datetime(start, end, BERLIN).isoformat(),
                currency=currency,
                status=random.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS)[0],
                shipping_amount_local=random.choices(
                    SHIPPING_OPTIONS[currency], weights=SHIPPING_WEIGHTS
                )[0],
                discount_amount_local=discount,
            )
        )

    duplicate_count = math.ceil(len(orders) * DUPLICATE_ORDER_RATE)
    orders.extend(random.sample(orders, k=duplicate_count))
    return orders


def build_order_lines(orders: list[Order], products: list[Product]) -> list[OrderLine]:
    lines = []
    line_seq = 1
    for order in orders:
        for product in random.choices(products, k=random.randint(1, 4)):
            lines.append(
                OrderLine(
                    order_line_id=f"LINE-{line_seq:08d}",
                    order_id=order.order_id,
                    product_id=product.product_id,
                    quantity=random.randint(1, 5),
                    unit_price_eur=product.price_eur,
                )
            )
            line_seq += 1
    return lines


def build_shipments(orders: list[Order]) -> list[Shipment]:
    shipments = []
    shipment_seq = 1
    for order in orders:
        if order.status not in {"shipped", "delivered"}:
            continue
        order_date = datetime.fromisoformat(order.order_date)
        occurred_at = (order_date + timedelta(days=random.randint(1, 4))).astimezone(ZURICH)
        recorded_at = maybe_delay(occurred_at)
        shipments.append(
            Shipment(
                shipment_id=f"SHIP-{shipment_seq:07d}",
                order_id=order.order_id,
                carrier=random.choice(CARRIERS),
                status="delivered" if order.status == "delivered" else "shipped",
                occurred_at=occurred_at.isoformat(),
                recorded_at=recorded_at.isoformat(),
            )
        )
        shipment_seq += 1
    return shipments


def build_refunds(orders: list[Order], order_lines: list[OrderLine]) -> list[Refund]:
    lines_by_order: dict[str, list[OrderLine]] = {}
    for line in order_lines:
        lines_by_order.setdefault(line.order_id, []).append(line)

    refunds = []
    refund_seq = 1
    for order in orders:
        if order.status not in REFUND_ELIGIBLE_STATUSES:
            continue
        if random.random() > REFUND_RATE_AMONG_ELIGIBLE:
            continue
        order_value = sum(
            line.quantity * line.unit_price_eur for line in lines_by_order.get(order.order_id, [])
        )
        if order_value <= 0:
            continue
        order_date = datetime.fromisoformat(order.order_date)
        occurred_at = (order_date + timedelta(days=random.randint(1, 10))).astimezone(UTC)
        recorded_at = maybe_delay(occurred_at)
        refunds.append(
            Refund(
                refund_id=f"REF-{refund_seq:06d}",
                order_id=order.order_id,
                amount_eur=round(order_value * random.uniform(0.5, 1.0), 2),
                reason=random.choice(REFUND_REASONS),
                occurred_at=occurred_at.isoformat(),
                recorded_at=recorded_at.isoformat(),
            )
        )
        refund_seq += 1
    return refunds


def write_parquet(records: list, out_dir: Path, name: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([record.model_dump() for record in records])
    df.to_parquet(out_dir / f"{name}.parquet", index=False)
    print(f"{name}: {len(df):,} rows -> {out_dir / f'{name}.parquet'}")


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    Faker.seed(args.seed)

    profile = PROFILES[args.profile]
    end = date.today()
    start = end - timedelta(days=365 * args.years)
    cutover = start + timedelta(days=int((end - start).days * 0.6))

    customers = build_customers(profile["customers"], start, end, cutover)
    products = build_products(profile["products"], start, end)
    orders = build_orders(profile["orders"], customers, start, end)
    order_lines = build_order_lines(orders, products)
    shipments = build_shipments(orders)
    refunds = build_refunds(orders, order_lines)

    write_parquet(customers, args.out, "customers")
    write_parquet(products, args.out, "products")
    write_parquet(orders, args.out, "orders")
    write_parquet(order_lines, args.out, "order_lines")
    write_parquet(shipments, args.out, "shipments")
    write_parquet(refunds, args.out, "refunds")


if __name__ == "__main__":
    main()
