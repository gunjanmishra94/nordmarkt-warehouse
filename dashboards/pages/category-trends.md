# Category trends

[Revenue overview](/) · [Fulfilment timing](/fulfilment-timing)

```sql order_lines_by_category
select
    fct_order_lines.order_id,
    fct_order_lines.order_date,
    fct_order_lines.net_revenue_eur,
    dim_product.category
from main.fct_order_lines
inner join main.dim_product on fct_order_lines.product_id = dim_product.product_id
```

{% dropdown
    id="category_filter"
    data="order_lines_by_category"
    value_column="category"
    title="Category"
/%}

{% bar_chart
    data="order_lines_by_category"
    x="category"
    y="sum(net_revenue_eur)"
    order="sum(net_revenue_eur) desc"
    y_fmt="eur1m"
    title="Net revenue by category"
/%}

{% line_chart
    data="order_lines_by_category"
    x="order_date"
    y="sum(net_revenue_eur)"
    series="category"
    date_grain="month"
    y_fmt="eur1m"
    filters=["category_filter"]
    title="Revenue by category, over time"
/%}

{% table
    data="order_lines_by_category"
    filters=["category_filter"]
    title="Category detail"
%}
    {% dimension value="category" /%}
    {% measure value="sum(net_revenue_eur)" fmt="eur1m" /%}
    {% measure value="count(distinct order_id)" title="Orders" /%}
    {% measure
        value="sum(net_revenue_eur) / nullif(count(distinct order_id), 0)"
        fmt="eur2"
        title="Avg order value"
    /%}
{% /table %}
