import pytest
import simpy

from simulations.fish import Fish
from simulations.pond import Pond


class TestFish():
    @pytest.mark.parametrize("params", [
        {"id": 1, "type": "Catfish", "weight": 0.01},
        {"id": 1, "type": "Catfish", "weight": 1},
    ])
    def test_create_fish(self, params):
        pond = Pond(env=simpy.Environment(), id=1, type="Concrete_Pond")
        fish = Fish(pond=pond, **params)
        assert fish.id == 1
        assert fish.tag == f'Catfish_1'

    @pytest.mark.parametrize("params", [
        {},
        {"id": 1, "weight": 0.01},
        {"id": 1, "type": "Catfish"},
    ])
    def test_fail_create_invalid_fish(self, params):
        pond = Pond(env=simpy.Environment(), id=1, type="Concrete_Pond")
        with pytest.raises(TypeError):
            Fish(pond=pond, **params)
