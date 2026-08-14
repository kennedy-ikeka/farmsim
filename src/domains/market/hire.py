from src.models.action import HireActionState


# Default multiplier applied to the Fibonacci hire-cost sequence.
FARM_HAND_COST_MULT = 1


def _fib(n):
    """Fibonacci with fib(0)=1, fib(1)=1, fib(2)=2, fib(3)=3, fib(4)=5, ...
    This is the hire-cost sequence: 1, 1, 2, 3, 5, 8, 13, 21, ..."""
    a, b = 1, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def _hand_spawn_position(farm):
    """Pick a shed-adjacent tile for a newly hired hand.

    The four center tiles are checked in NWSE order. The first free one
    (zero occupants) is chosen. If all are occupied, the one with the fewest
    occupants wins (ties broken by NWSE order). Occupants are the farmer and
    all current hands — Farmer/Farm Hand CAN occupy the same tile.
    """
    half_r = len(farm.tiles) // 2
    half_c = (len(farm.tiles[0]) if farm.tiles else 0) // 2
    candidates = [
        (half_r - 1, half_c - 1),  # NW
        (half_r, half_c - 1),      # SW
        (half_r - 1, half_c),      # NE
        (half_r, half_c),          # SE
    ]
    all_positions = [tuple(farm.farmer)] + [tuple(h) for h in farm.hands]
    counts = [sum(1 for p in all_positions if p == pos) for pos in candidates]

    # First free tile.
    for i, count in enumerate(counts):
        if count == 0:
            return list(candidates[i])

    # None free — least occupied, NWSE tie-break via order.
    min_count = min(counts)
    for i, count in enumerate(counts):
        if count == min_count:
            return list(candidates[i])


def hire(state, action: HireActionState) -> dict:
    """Hire a farm hand for the day, charging the escalating Fibonacci cost.

    Cost is `FARM_HAND_COST_MULT * fib(hires_today)`, where `hires_today` is
    the number of hires already made today (the sequence resets each day).
    No-ops (silent) when the farm cannot afford the next hire. On success,
    deducts the cost, increments `hires_today`, and appends a new hand
    position to `farm.hands` — shed-adjacent, chosen by NWSE free-space
    preference then least-occupant tie-break.
    """
    farm = state.farms[state.player]
    cost = FARM_HAND_COST_MULT * _fib(farm.hires_today)
    if farm.money < cost:
        return {"cost": cost, "position": None, "hired": False}

    farm.money -= cost
    farm.hires_today += 1
    position = _hand_spawn_position(farm)
    farm.hands.append(position)
    return {"cost": cost, "position": position, "hired": True}


def get_valid_hire_actions(player) -> list[HireActionState]:
    """Valid HIRE action — present iff the farm can afford the next hire.

    HIRE no-ops when `farm.money < FARM_HAND_COST_MULT * _fib(hires_today)`.
    Returns a single HIRE action (count is implicit — one hand per call).
    """
    farm = player.farms[player.player]
    cost = FARM_HAND_COST_MULT * _fib(farm.hires_today)
    if farm.money < cost:
        return []
    return [HireActionState(type="HIRE")]