"""Crop growth configuration (the GAME CONFIG block from gameplay/roadmap.md).

Sourced from the Object Types table in README.md. These values drive seed
purchasing, planting, and the decay schedule.
"""

# Per-crop growth parameters.
#   yield_type        — "one-time" (single harvest) or "ongoing" (repeated yields)
#   seed_cost         — fixed market price to buy one seed
#   first_yield_day   — days from planting before the first yield is available
#   max_yield_day     — day (from planting) of the last scheduled yield; decay
#                       begins one day after this for both yield types
#   max_yield         — total harvestable units a single plant can produce
CROP_CONFIG = {
    "WHEAT": {
        "yield_type": "one-time",
        "seed_cost": 10,
        "first_yield_day": 2,
        "max_yield_day": 4,
        "max_yield": 6,
    },
    "CARROT": {
        "yield_type": "one-time",
        "seed_cost": 20,
        "first_yield_day": 2,
        "max_yield_day": 3,
        "max_yield": 4,
    },
    "TOMATO": {
        "yield_type": "ongoing",
        "seed_cost": 50,
        "first_yield_day": 8,
        "max_yield_day": 11,
        "max_yield": 4,
    },
    "STRAWBERRY": {
        "yield_type": "ongoing",
        "seed_cost": 100,
        "first_yield_day": 10,
        "max_yield_day": 16,
        "max_yield": 4,
    },
    "MELON": {
        "yield_type": "one-time",
        "seed_cost": 80,
        "first_yield_day": 10,
        "max_yield_day": 10,
        "max_yield": 6,
    },
}