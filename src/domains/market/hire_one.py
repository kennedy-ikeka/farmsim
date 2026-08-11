"""Per-unit hire helper — hires exactly one farm hand at the escalating
Fibonacci cost. Used by the market interleave loop (single-shot: one attempt
per order)."""
from src.models.action import HireActionState

from src.domains.market.hire import _fib, _hand_spawn_position


def hire_one(farm, action: HireActionState) -> tuple[bool, dict]:
    """Hire one farm hand for `farm`, charging `fib(hires_today)` and spawning
    the new hand at a shed-adjacent tile. Returns `(success, unit_occurred)`.

    Fails when the farm cannot afford the next hire.
    """
    cost = _fib(farm.hires_today)
    if farm.money < cost:
        return False, {"cost": cost, "position": None, "hired": False}
    farm.money -= cost
    farm.hires_today += 1
    position = _hand_spawn_position(farm)
    farm.hands.append(position)
    return True, {"cost": cost, "position": position, "hired": True}