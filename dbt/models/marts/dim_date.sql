{# Date spine covering the dataset plus margin. Generated, not sourced. #}
with spine as (
    select cast(range as date) as date_day
    from range(date '2025-12-01', date '2026-09-01', interval 1 day)
)

select
    date_day,
    cast(date_trunc('week', date_day) as date) as week_start,
    cast(date_trunc('month', date_day) as date) as month_start,
    isoyear(date_day) as iso_year,
    week(date_day) as iso_week,
    isodow(date_day) as iso_day_of_week,
    dayname(date_day) as day_name,
    isodow(date_day) in (6, 7) as is_weekend
from spine
