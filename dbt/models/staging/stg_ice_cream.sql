-- One row per area, year, and measure, with FAO names renamed to words SQL can use.
-- Aggregates such as World stay in this view. The country filter happens in the next layer,
-- so you can still query the World row and see what was kept out of the mart.

select
    cast(Area_Code as int64) as area_code,
    Area as area_name,
    cast(Item_Code as int64) as item_code,
    Item as item_name,
    cast(Element_Code as int64) as element_code,
    Element as element_name,
    cast(Year as int64) as year,
    Unit as unit,
    cast(Value as float64) as value,
    Flag as flag
from {{ source('raw', 'ice_cream_sua') }}
where cast(Item_Code as int64) = 910
    and Value is not null
    and cast(Element_Code as int64) in (
        5510,  -- production, tonnes
        5610,  -- import quantity, tonnes
        5910,  -- export quantity, tonnes
        5141,  -- food supply, tonnes
        665    -- food supply, grams per person per day
    )
