"""Animal configuration — fixed costs and production parameters per animal.

Sourced from the Object Types table in README.md.
"""

ANIMAL_CONFIG = {
    "GOOSE": {
        "cost": 300,
        "structure": "COOP",
        "product": "EGG",
        "first_yield_day": 4,
        "interval": 1,   # produces every day
        "max_held": 4,
    },
    "COW": {
        "cost": 400,
        "structure": "PASTURE",
        "product": "MILK",
        "first_yield_day": 8,
        "interval": 2,   # produces every two days
        "max_held": 6,
    },
    "SHEEP": {
        "cost": 500,
        "structure": "PASTURE",
        "product": "WOOL",
        "first_yield_day": 6,
        "interval": 3,   # produces every three days
        "max_held": 6,
    },
}