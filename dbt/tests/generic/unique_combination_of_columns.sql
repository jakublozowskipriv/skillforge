{#
  Multi-column uniqueness (like dbt_utils.unique_combination_of_columns) without a package
  dependency. A dbt test is just a query returning *failing rows*: zero rows = pass.
#}
{% test unique_combination_of_columns(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}
