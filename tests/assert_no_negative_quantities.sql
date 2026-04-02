-- Fails (returns rows) if any order line has a zero or negative quantity.
select
    order_line_id,
    order_id,
    quantity
from {{ ref('stg_order_lines') }}
where quantity <= 0
