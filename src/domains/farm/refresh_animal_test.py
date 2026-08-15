"""Tests for end-of-day animal refresh: escape, care bonus, fertilizer, production."""
from types import SimpleNamespace

import pytest

from src.domains.farm.refresh_animal import refresh_animal
from src.models.farm import AnimalState


def _structure(kind="COOP", animal="GOOSE", fed_today=False, cared_today=False,
               consecutive_unfed=0, yield_units=0, pending_care_bonus=0,
               fertilizer_available=0, placed_day=0):
    return AnimalState(
        kind=kind, animal=animal,
        fed_today=fed_today, cared_today=cared_today,
        consecutive_unfed=consecutive_unfed,
        yield_units=yield_units,
        pending_care_bonus=pending_care_bonus,
        fertilizer_available=fertilizer_available,
        placed_day=placed_day,
    )


def _state(day):
    """Minimal stand-in for GameState — refresh_animal only reads `state.day`."""
    return SimpleNamespace(day=day)


class TestRefreshAnimal:
    """Tests for `refresh_animal`."""

    # ---------------------------------------------------------------------------
    # Empty structure — no animal housed.
    # ---------------------------------------------------------------------------

    def test_empty_structure_resets_daily_flags(self):
        tile = _structure(animal=None, fed_today=True, cared_today=True)
        refresh_animal(tile)
        assert tile.animal is None
        assert tile.fed_today is False
        assert tile.cared_today is False

    # ---------------------------------------------------------------------------
    # Escape — two consecutive missed feeds.
    # ---------------------------------------------------------------------------

    def test_unfed_first_miss_increments_counter(self):
        tile = _structure(animal="GOOSE", fed_today=False, consecutive_unfed=0)
        refresh_animal(tile)
        assert tile.animal == "GOOSE"  # survives first miss
        assert tile.consecutive_unfed == 1
        assert tile.fed_today is False

    def test_unfed_second_miss_animal_escapes(self):
        tile = _structure(animal="GOOSE", fed_today=False, consecutive_unfed=1)
        refresh_animal(tile)
        assert tile.animal is None  # escaped
        assert tile.consecutive_unfed == 0
        assert tile.fed_today is False
        assert tile.cared_today is False
        assert tile.fertilizer_available == 0

    @pytest.mark.parametrize("animal, kind", [
        ("GOOSE", "COOP"),
        ("COW", "PASTURE"),
        ("SHEEP", "PASTURE"),
    ])
    def test_escape_applies_to_every_animal_type(self, animal, kind):
        tile = _structure(kind=kind, animal=animal, fed_today=False, consecutive_unfed=1)
        refresh_animal(tile)
        assert tile.animal is None

    def test_structure_stays_after_escape(self):
        """The structure (COOP/PASTURE) stays on the tile — only the animal leaves."""
        tile = _structure(kind="COOP", animal="GOOSE", fed_today=False, consecutive_unfed=1)
        refresh_animal(tile)
        assert tile.animal is None
        assert tile.kind == "COOP"  # structure preserved

    # ---------------------------------------------------------------------------
    # Fed animal — counter reset, fertilizer available, daily flags reset.
    # ---------------------------------------------------------------------------

    def test_fed_resets_consecutive_unfed(self):
        tile = _structure(animal="GOOSE", fed_today=True, consecutive_unfed=1)
        refresh_animal(tile)
        assert tile.animal == "GOOSE"
        assert tile.consecutive_unfed == 0

    def test_surviving_animal_makes_one_fertilizer_available(self):
        tile = _structure(animal="GOOSE", fed_today=True, fertilizer_available=0)
        refresh_animal(tile)
        assert tile.fertilizer_available == 1

    def test_fertilizer_does_not_accumulate_past_one(self):
        """A surviving animal sets fertilizer_available to 1, regardless of prior value."""
        tile = _structure(animal="GOOSE", fed_today=True, fertilizer_available=1)
        refresh_animal(tile)
        assert tile.fertilizer_available == 1  # still 1, not 2

    def test_resets_daily_flags_for_survivor(self):
        tile = _structure(animal="GOOSE", fed_today=True, cared_today=True)
        refresh_animal(tile)
        assert tile.fed_today is False
        assert tile.cared_today is False

    # ---------------------------------------------------------------------------
    # Care bonus banking — fed AND cared, capped by max_held - yield.
    # ---------------------------------------------------------------------------

    def test_banks_care_bonus_when_fed_and_cared(self):
        tile = _structure(animal="GOOSE", fed_today=True, cared_today=True,
                          yield_units=0, pending_care_bonus=0)
        refresh_animal(tile)
        assert tile.pending_care_bonus == 1

    def test_no_care_bonus_when_fed_but_not_cared(self):
        tile = _structure(animal="GOOSE", fed_today=True, cared_today=False,
                          pending_care_bonus=0)
        refresh_animal(tile)
        assert tile.pending_care_bonus == 0

    def test_no_care_bonus_when_at_max_held(self):
        """GOOSE max_held=4; yield_units=4 → no room → no bonus banked."""
        tile = _structure(animal="GOOSE", fed_today=True, cared_today=True,
                          yield_units=4, pending_care_bonus=0)
        refresh_animal(tile)
        assert tile.pending_care_bonus == 0

    def test_banks_bonus_when_below_max_held(self):
        """GOOSE max_held=4; yield_units=2 → room for 1 more → bonus banked."""
        tile = _structure(animal="GOOSE", fed_today=True, cared_today=True,
                          yield_units=2, pending_care_bonus=0)
        refresh_animal(tile)
        assert tile.pending_care_bonus == 1

    def test_accumulates_care_bonus_across_days(self):
        tile = _structure(animal="GOOSE", fed_today=True, cared_today=True,
                          yield_units=0, pending_care_bonus=2)
        refresh_animal(tile)
        assert tile.pending_care_bonus == 3

    # ---------------------------------------------------------------------------
    # Fed-but-not-cared path: no bonus, but fertilizer + flag resets still apply.
    # ---------------------------------------------------------------------------

    def test_fed_only_still_sets_fertilizer_and_resets_flags(self):
        tile = _structure(animal="COW", fed_today=True, cared_today=False,
                          pending_care_bonus=0, fertilizer_available=0)
        refresh_animal(tile)
        assert tile.animal == "COW"
        assert tile.pending_care_bonus == 0
        assert tile.fertilizer_available == 1
        assert tile.fed_today is False
        assert tile.cared_today is False


class TestRefreshAnimalProduction:
    """Tests for scheduled production payout (requires `state` with `day`)."""

    # ---------------------------------------------------------------------------
    # GOOSE: first_yield_day=4, interval=1, max_held=4 → produces every day from day 4.
    # ---------------------------------------------------------------------------

    def test_goose_produces_base_one_on_first_yield_day(self):
        tile = _structure(animal="GOOSE", fed_today=True, placed_day=0,
                          yield_units=0, pending_care_bonus=0)
        refresh_animal(tile, _state(day=4))
        assert tile.yield_units == 1  # base 1, no bonus banked before production
        assert tile.pending_care_bonus == 0  # bank resets on production day

    def test_goose_produces_every_day_after_first_yield(self):
        """GOOSE interval=1 → production on days 4, 5, 6, 7 (if not harvested)."""
        tile = _structure(animal="GOOSE", fed_today=True, placed_day=0,
                          yield_units=0, pending_care_bonus=0)
        refresh_animal(tile, _state(day=4))
        assert tile.yield_units == 1
        # Day 5: fed again, yield accumulates (no harvest in between).
        tile.fed_today = True
        refresh_animal(tile, _state(day=5))
        assert tile.yield_units == 2

    def test_goose_does_not_produce_before_first_yield_day(self):
        tile = _structure(animal="GOOSE", fed_today=True, placed_day=0,
                          yield_units=0, pending_care_bonus=0)
        refresh_animal(tile, _state(day=3))
        assert tile.yield_units == 0  # not yet day 4

    # ---------------------------------------------------------------------------
    # COW: first_yield_day=8, interval=2, max_held=6 → produces on days 8, 10, 12, ...
    # ---------------------------------------------------------------------------

    def test_cow_produces_on_first_yield_day(self):
        tile = _structure(kind="PASTURE", animal="COW", fed_today=True,
                          placed_day=0, yield_units=0, pending_care_bonus=0)
        refresh_animal(tile, _state(day=8))
        assert tile.yield_units == 1

    def test_cow_skips_off_interval_day(self):
        """COW interval=2 → no production on day 9 (between 8 and 10)."""
        tile = _structure(kind="PASTURE", animal="COW", fed_today=True,
                          placed_day=0, yield_units=0, pending_care_bonus=0)
        refresh_animal(tile, _state(day=9))
        assert tile.yield_units == 0

    def test_cow_produces_on_next_interval_day(self):
        tile = _structure(kind="PASTURE", animal="COW", fed_today=True,
                          placed_day=0, yield_units=0, pending_care_bonus=0)
        refresh_animal(tile, _state(day=8))
        tile.fed_today = True
        refresh_animal(tile, _state(day=10))
        assert tile.yield_units == 2

    # ---------------------------------------------------------------------------
    # SHEEP: first_yield_day=6, interval=3, max_held=6 → produces on days 6, 9, 12, ...
    # ---------------------------------------------------------------------------

    def test_sheep_produces_on_first_yield_day(self):
        tile = _structure(kind="PASTURE", animal="SHEEP", fed_today=True,
                          placed_day=0, yield_units=0, pending_care_bonus=0)
        refresh_animal(tile, _state(day=6))
        assert tile.yield_units == 1

    def test_sheep_skips_off_interval_days(self):
        """SHEEP interval=3 → no production on days 7 or 8."""
        tile = _structure(kind="PASTURE", animal="SHEEP", fed_today=True,
                          placed_day=0, yield_units=0, pending_care_bonus=0)
        refresh_animal(tile, _state(day=7))
        assert tile.yield_units == 0
        tile.fed_today = True
        refresh_animal(tile, _state(day=8))
        assert tile.yield_units == 0

    # ---------------------------------------------------------------------------
    # Care bonus payout — banked bonus is added on production day if fed today.
    # ---------------------------------------------------------------------------

    def test_care_bonus_paid_out_on_production_day_when_fed(self):
        """A fed+cared animal banks +1 each day; on production day the bank is
        paid out on top of the base 1, then the bank resets to 0.

        Banking runs BEFORE production, so on the production day itself the
        bonus is banked (+1 → 3) and then paid out (1 + 3 = 4).
        """
        # GOOSE: bank 2 bonus on days 2, 3 (fed+cared, no production yet).
        tile = _structure(animal="GOOSE", fed_today=True, cared_today=True,
                          placed_day=0, yield_units=0, pending_care_bonus=2)
        # Day 4 = first production day, fed+cared today → bank +1 (→3),
        # then produced = 1 + 3 = 4.
        refresh_animal(tile, _state(day=4))
        assert tile.yield_units == 4
        assert tile.pending_care_bonus == 0  # bank reset

    def test_care_bonus_not_paid_when_not_fed_on_production_day(self):
        """If the animal was not fed today, the banked bonus is NOT paid out
        (but the bank still resets to 0 on a production day)."""
        tile = _structure(animal="GOOSE", fed_today=False, cared_today=False,
                          placed_day=0, yield_units=0, pending_care_bonus=2)
        refresh_animal(tile, _state(day=4))
        # Not fed → escapes check first: consecutive_unfed was 0, now 1, survives.
        # Production: produced = 1 + (bonus if fed_today else 0) = 1 + 0 = 1.
        assert tile.yield_units == 1
        assert tile.pending_care_bonus == 0  # bank resets on production day

    def test_care_bonus_banked_same_day_then_paid_out(self):
        """On a production day, the fed+cared bonus is banked FIRST, then paid
        out as part of the same production, so it's not lost."""
        # GOOSE at day 4 (production day), fed+cared, no prior bank.
        tile = _structure(animal="GOOSE", fed_today=True, cared_today=True,
                          placed_day=0, yield_units=0, pending_care_bonus=0)
        refresh_animal(tile, _state(day=4))
        # Bank +1 (yield 0 < max 4), then produced = 1 + 1 = 2.
        assert tile.yield_units == 2
        assert tile.pending_care_bonus == 0  # reset after payout

    # ---------------------------------------------------------------------------
    # max_held cap — yield_units cannot exceed max_held.
    # ---------------------------------------------------------------------------

    def test_yield_capped_at_max_held(self):
        """GOOSE max_held=4; yield_units=3, production of base 1 → capped at 4."""
        tile = _structure(animal="GOOSE", fed_today=True, placed_day=0,
                          yield_units=3, pending_care_bonus=0)
        refresh_animal(tile, _state(day=4))
        assert tile.yield_units == 4  # 3 + 1, capped at 4

    def test_yield_does_not_exceed_max_held_with_bonus(self):
        """GOOSE max_held=4; yield=3, bonus=2 → 3+1+2=6 but capped at 4."""
        tile = _structure(animal="GOOSE", fed_today=True, cared_today=True,
                          placed_day=0, yield_units=3, pending_care_bonus=2)
        refresh_animal(tile, _state(day=4))
        assert tile.yield_units == 4  # capped
        assert tile.pending_care_bonus == 0  # bank reset

    # ---------------------------------------------------------------------------
    # No state / no placed_day → no production (backward compat).
    # ---------------------------------------------------------------------------

    def test_no_state_means_no_production(self):
        tile = _structure(animal="GOOSE", fed_today=True, placed_day=0,
                          yield_units=0, pending_care_bonus=0)
        refresh_animal(tile)  # state=None
        assert tile.yield_units == 0

    def test_no_placed_day_means_no_production(self):
        tile = _structure(animal="GOOSE", fed_today=True, placed_day=None,
                          yield_units=0, pending_care_bonus=0)
        refresh_animal(tile, _state(day=4))
        assert tile.yield_units == 0