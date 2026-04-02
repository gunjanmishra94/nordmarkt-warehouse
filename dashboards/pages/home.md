# Revenue overview

[Category trends](/category-trends) · [Fulfilment timing](/fulfilment-timing)

Net revenue = quantity × unit price, minus this line's share of the order's discount. Shipping is excluded — see the main README's "What the numbers mean".

{% big_value
    data="main.fct_order_lines"
    value="sum(net_revenue_eur)"
    fmt="eur1m"
    title="Total net revenue"
/%}

{% big_value
    data="main.fct_order_lines"
    value="count(distinct order_id)"
    fmt="num0"
    title="Total orders"
/%}

{% line_chart
    data="main.fct_order_lines"
    x="order_date"
    y="sum(net_revenue_eur)"
    date_grain="month"
    y_fmt="eur1m"
    title="Net revenue by month"
/%}

{% table
    data="main.fct_order_lines"
    title="Revenue by currency"
%}
    {% dimension value="currency" /%}
    {% measure value="sum(net_revenue_eur)" fmt="eur1m" /%}
    {% measure value="count(distinct order_id)" title="Orders" /%}
{% /table %}
