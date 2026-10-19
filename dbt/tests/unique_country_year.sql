select
    area_code,
    year,
    count(*) as row_count
from {{ ref('int_ice_cream_country_year') }}
group by 1, 2
having count(*) > 1
