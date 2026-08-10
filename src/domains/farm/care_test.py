import pytest

from tests.fixtures import _make_env
from src.domains.farm.care import care
from src.models.action import CareActionState
from src.models.environment import StepState
from src.models.farm import AnimalState, PlantState


def _structure(kind="COOP", animal="GOOSE", cared_today=False):
    return AnimalState(kind=kind, animal=animal, cared_today=cared_today)


@pytest.mark.parametrize("kind, animal", [
    ("COOP", "GOOSE"),
    ("PASTURE", "COW"),
    ("PASTURE", "SHEEP"),
])
def test_care_marks_cared_today(kind, animal):
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _structure(kind=kind, animal=animal)

    care(farm, farm.farmer, CareActionState(type="CARE"))

    assert farm.tiles[5][5].cared_today is True


def test_care_noop_when_already_cared_today():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _structure(cared_today=True)

    care(farm, farm.farmer, CareActionState(type="CARE"))

    assert farm.tiles[5][5].cared_today is True  # unchanged


def test_care_noop_on_empty_structure():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = AnimalState(kind="COOP", animal=None)

    care(farm, farm.farmer, CareActionState(type="CARE"))

    assert farm.tiles[5][5].cared_today is False


def test_care_noop_on_non_structure_tile():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = PlantState(crop="WHEAT", planted_day=0, max_lifespan_step=120)

    care(farm, farm.farmer, CareActionState(type="CARE"))

    assert isinstance(farm.tiles[5][5], PlantState)  # untouched


def test_care_noop_on_empty_tile():
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]

    care(farm, farm.farmer, CareActionState(type="CARE"))

    assert farm.tiles[5][5] is None


@pytest.mark.parametrize("bad_pos", [None, [5], [], [5, 5, 0], (-1, 5), (5, -1)])
def test_care_noop_on_malformed_or_negative_position(bad_pos):
    env = _make_env(farmer=(5, 5))
    farm = env.state.farms[0]
    farm.tiles[5][5] = _structure()
    pos = list(bad_pos) if isinstance(bad_pos, tuple) else bad_pos

    care(farm, pos, CareActionState(type="CARE"))

    assert farm.tiles[5][5].cared_today is False


def test_care_noop_out_of_bounds():
    env = _make_env(rows=5, cols=5, farmer=(4, 4))
    farm = env.state.farms[0]
    farm.tiles[4][4] = _structure()

    care(farm, [5, 0], CareActionState(type="CARE"))

    assert farm.tiles[4][4].cared_today is False


def test_step_dispatches_care():
    env = _make_env(farmer=(3, 3))
    farm = env.state.farms[0]
    farm.tiles[3][3] = _structure(kind="COOP", animal="GOOSE")

    step = StepState(
        farmer=CareActionState(type="CARE"),
        hands=[],
        market=[],
    )
    env.step(step)

    assert env.state.farms[0].tiles[3][3].cared_today is True