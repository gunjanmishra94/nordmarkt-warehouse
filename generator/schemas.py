"""Pydantic contracts for the raw records the generator produces.

`Customer.zip_code` / `Customer.postal_code` are deliberately both optional: rows
generated before the cutover date only populate `zip_code`, rows after only
populate `postal_code`. This models a source system that renamed the column
partway through history, and staging is responsible for coalescing the two.
"""

from pydantic import BaseModel


class Customer(BaseModel):
    customer_id: str
    first_name: str
    last_name: str
    email: str
    country: str
    city: str
    address_line: str
    zip_code: str | None
    postal_code: str | None
    tier: str
    signup_date: str
    created_at: str


class Product(BaseModel):
    product_id: str
    name: str
    category: str
    supplier: str
    price_eur: float
    created_at: str


class Order(BaseModel):
    order_id: str
    customer_id: str
    order_date: str
    currency: str
    status: str


class OrderLine(BaseModel):
    order_line_id: str
    order_id: str
    product_id: str
    quantity: int
    unit_price_eur: float


class Shipment(BaseModel):
    shipment_id: str
    order_id: str
    carrier: str
    status: str
    occurred_at: str
    recorded_at: str


class Refund(BaseModel):
    refund_id: str
    order_id: str
    amount_eur: float
    reason: str
    occurred_at: str
    recorded_at: str
