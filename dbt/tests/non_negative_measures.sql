-- Tonnes and kilograms on the mart cannot be negative. Null production is allowed.
select
    area_code,
    year
from {{ ref('mart_ice_cream_country_year') }}
where production_tonnes < 0
    or import_tonnes < 0
    or export_tonnes < 0
    or food_supply_tonnes < 0
    or kg_per_person_year < 0
