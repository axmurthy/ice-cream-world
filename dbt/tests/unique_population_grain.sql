select
    area_code,
    year,
    count(*) as row_count
from {{ ref('stg_population') }}
group by 1, 2
having count(*) > 1
