from src.models.action import SellActionState


def sell(state, action: SellActionState) -> dict:
    """Sell `count` of `item` from the shed into the market at current price."""
    farm = state.farms[state.player]
    shed = state.privates[state.player].shed
    available = getattr(shed, action.item, 0)

    count = min(action.count, available)
    price = getattr(state.market.prices, action.item, 0)
    if count <= 0:
        return {"item": action.item, "count": 0, "price": price, "revenue": 0}

    setattr(shed, action.item, available - count)
    inventory = getattr(state.market.inventory, action.item, 0)

    setattr(state.market.inventory, action.item, inventory + count)
    farm.money += count * price
    return {"item": action.item, "count": count, "price": price, "revenue": count * price}