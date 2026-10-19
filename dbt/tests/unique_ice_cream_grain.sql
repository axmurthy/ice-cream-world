-- The staging grain is one area, one year, one measure.
select
    area_code,
    year,
    element_code,
    count(*) as row_count
from {{ ref('stg_ice_cream') }}
group by 1, 2, 3
having count(*) > 1
