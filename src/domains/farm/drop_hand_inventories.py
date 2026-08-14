"""End-of-day hand inventory drop — move hired-hands' carried items to the shed.

At day rollover, hired hands leave. Each hand's inventory (`priv.inventories[i+1]`)
is dropped into the shed, capped by `shed_capacity`; overflow is discarded. Items
that are not valid shed fields are skipped. The main farmer's inventory
(`inventories[0]`) is untouched — the farmer persists across days.
"""
from src.models.farm import FarmState
from src.models.player import PrivateState


def drop_hand_inventories_to_shed(farm: FarmState, priv: PrivateState,
                                  shed_capacity: int) -> None:
    """Move each hand's inventory into `priv.shed`, capped by `shed_capacity`.

    `inventories[0]` is the farmer; hands are indices `1..len(farm.hands)`.
    For each hand inventory, each item is moved `min(count, space)` units into
    the matching shed field; leftover units are left in the hand inventory
    (and discarded with the hand when the caller clears it).
    """
    # inventories[0] is the farmer; hands are indices 1..len(hands).
    for i in range(1, len(farm.hands) + 1):
        if i >= len(priv.inventories):
            break
        inv = priv.inventories[i]
        for item in type(inv).model_fields:
            count = getattr(inv, item, 0)
            if count <= 0:
                continue
            total_in_shed = sum(getattr(priv.shed, f) for f in type(priv.shed).model_fields)
            space = max(0, shed_capacity - total_in_shed)
            to_move = min(count, space)
            if to_move <= 0:
                continue
            if not hasattr(priv.shed, item):
                continue  # not a valid shed field
            setattr(priv.shed, item, getattr(priv.shed, item, 0) + to_move)
            setattr(inv, item, count - to_move)