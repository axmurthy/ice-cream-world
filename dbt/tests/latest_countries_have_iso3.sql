select area_code, area_name
from {{ ref('mart_ice_cream_latest') }}
where iso3 is null
