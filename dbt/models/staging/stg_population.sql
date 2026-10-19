-- FAO publishes population in thousands of people. Both units stay on the view
-- so the * 1000 conversion is visible. If FAO repeats a country-year, keep the
-- official figure (flag A) ahead of an estimate.

with source as (
    select
        cast(Area_Code as int64) as area_code,
        Area as area_name,
        cast(Year as int64) as year,
        cast(Value as float64) as population_thousands,
        Flag as flag
    from {{ source('raw', 'population') }}
    where cast(Element_Code as int64) = 511
        and Value is not null
)

select
    area_code,
    area_name,
    year,
    population_thousands,
    population_thousands * 1000 as population_persons,
    flag
from source
qualify row_number() over (
    partition by area_code, year
    order by case flag when 'A' then 1 when 'X' then 2 when 'E' then 3 else 4 end
) = 1
