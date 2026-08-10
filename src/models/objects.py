
from typing_extensions import Literal


CROPS = Literal['WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON']
ANIMALS = Literal['GOOSE', 'COW', 'SHEEP']

# Only wheat and fertilizer can be bought back via BUY_PRODUCT.
BUYABLE_PRODUCTS = Literal['WHEAT', 'FERTILIZER']

# Every product can be sold via SELL.
SELLABLE_PRODUCTS = Literal['WHEAT', 'CARROT', 'TOMATO', 'STRAWBERRY', 'MELON', 'EGG', 'MILK', 'WOOL', 'FERTILIZER']