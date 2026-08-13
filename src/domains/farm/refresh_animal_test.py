"""Tests for end-of-day animal refresh: escape, care bonus, fertilizer."""
import pytest

from src.domains.farm.refresh_animal import refresh_animal
from src.models.farm import AnimalState


def _structure(kind="COOP", animal="GOOSE", fed_today=False, cared_today=False,
               consecutive_unfed=0, yield_units=0, pending_care_bonus=0,
               fertilizer_available=0):
    return AnimalState(
        kind=kind, animal=animal,
        fed_today=fed_today, cared_today=cared_today,
        consecutive_unfed=consecutive_unfed,
        yield_units=yield_units,
        pending_care_bonus=pending_care_bonus,
        fertilizer_available=fertilizer_available,
    )


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