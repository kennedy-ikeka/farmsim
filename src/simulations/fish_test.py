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

    @pytest.mark.parametrize("params", [
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            "hunger_rate": 0.5,
            "hunger_weight": 0.0005,
            "waste_weight": 0.0005
        },
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 1, "stomach": 10},
            "hunger_rate": 0.9,
            "hunger_weight": 0.09,
            "waste_weight": 0.01
        }
    ])
    def test_fish_stomach(self, params):
        fish_params = params['fish_params']
        hunger_rate = params['hunger_rate']
        hunger_weight = params['hunger_weight']
        waste_weight = params['waste_weight']
        
        pond = Pond(env=simpy.Environment(), id=1, type="Concrete_Pond")
        fish = Fish(pond=pond, **fish_params)

        fish_hunger_rate = round(fish.get_hunger_rate(), 5)
        fish_hunger_weight = round(fish.get_hunger_weight(), 5)
        fish_waste_weight = round(fish.get_waste_weight(), 5)

        assert fish_hunger_rate == hunger_rate
        assert fish_hunger_weight == hunger_weight
        assert fish_waste_weight == waste_weight

    @pytest.mark.parametrize("params", [
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            "feed_weight": 0.0005,
            "feed_rate": 1,
            "stomach_level": 100,
            "fish_weight": 0.0105,
        },
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            "feed_weight": 0.0001,
            "feed_rate": 1,
            "stomach_level": 60,
            "fish_weight": 0.0101,
        },
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            "feed_weight": 0.0005,
            "feed_rate": 1.2,
            "stomach_level": 100,
            "fish_weight": 0.01042,
        },
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            "feed_weight": 0,
            "feed_rate": 1,
            "stomach_level": 50,
            "fish_weight": 0.01,
        },
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            "feed_weight": 0.01,
            "feed_rate": 1,
            "stomach_level": 100,
            "fish_weight": 0.0105,
        },
    ])
    def test_eat(self, params):
        fish_params = params['fish_params']
        feed_weight = params['feed_weight']
        feed_rate = params['feed_rate']
        stomach_level = params['stomach_level']
        fish_weight = params['fish_weight']
        
        pond = Pond(env=simpy.Environment(), id=1, type="Concrete_Pond")
        fish = Fish(pond=pond, **fish_params)

        eat_process = fish.eat(feed_weight, feed_rate)
        if feed_weight:
            next(eat_process)
            next(eat_process)
            next(eat_process)

        assert stomach_level == round(fish.stomach.level, 5)
        assert fish_weight == round(fish.weight.level, 5)

    @pytest.mark.parametrize("params", [
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            "excrete_weight": 0.0005,
            "stomach_level": 0,
            "fish_weight": 0.0095,
        },
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            "excrete_weight": 0.0001,
            "stomach_level": 40,
            "fish_weight": 0.00998,
        },
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            "excrete_weight": 0.,
            "stomach_level": 50,
            "fish_weight": 0.01,
        },
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            "excrete_weight": 0.01,
            "stomach_level": 0,
            "fish_weight": 0.0095,
        },
    ])
    def test_excrete(self, params):
        fish_params = params['fish_params']
        excrete_weight = params['excrete_weight']
        stomach_level = params['stomach_level']
        fish_weight = params['fish_weight']
        
        pond = Pond(env=simpy.Environment(), id=1, type="Concrete_Pond")
        fish = Fish(pond=pond, **fish_params)

        eat_process = fish.excrete(excrete_weight)
        if excrete_weight:
            next(eat_process)
            next(eat_process)

        assert stomach_level == round(fish.stomach.level, 5)
        assert fish_weight == round(fish.weight.level, 5)

    @pytest.mark.parametrize("params", [
        [
            {
                "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
                "hunt_rate": 0.5,
                "rank": 0.35714
            },
            {
                "fish_params": {"id": 2, "type": "Catfish", "weight": 0.01, "stomach": 10},
                "hunt_rate": 0.9,
                "rank": 0.64286
            }
        ],
        [
            {
                "fish_params": {"id": 1, "type": "Catfish", "weight": 0.09, "stomach": 90},
                "hunt_rate": 0.3,
                "rank": 0.14286
            },
            {
                "fish_params": {"id": 2, "type": "Catfish", "weight": 0.04, "stomach": 10},
                "hunt_rate": 1.8,
                "rank": 0.85714
            }
        ],
    ])
    def test_feeding_rank(self, params):        
        pond = Pond(env=simpy.Environment(), id=1, type="Concrete_Pond")
        for p in params:
            fish_params = p["fish_params"]
            f = Fish(pond=pond, **fish_params)

        for p in params:
            fish_params = p["fish_params"]
            hunt_rate = p["hunt_rate"]
            rank = p["rank"]
            fish = pond.get_fish_by_id(fish_params["id"])

            f_hunt_rate = fish.get_hunt_rate()
            assert hunt_rate == round(f_hunt_rate, 5)

            f_rank = fish.get_feeding_rank()
            assert rank == round(f_rank, 5)

    @pytest.mark.parametrize("params", [
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50, "health": 100},
            "pond_health": 50,
            "pond_health_effect": 75,
            "stomach_health_effect": 0.0,
        },
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 1, "stomach": 10, "health": 20},
            "pond_health": 100,
            "pond_health_effect": 60,
            "stomach_health_effect": 0.0,
        },
        {
            "fish_params": {"id": 1, "type": "Catfish", "weight": 1, "stomach": 10, "health": 20},
            "pond_health": 50,
            "pond_health_effect": 35,
            "stomach_health_effect": 0.0,
        }
    ])
    def test_fish_health(self, params):
        fish_params = params['fish_params']
        pond_health = params['pond_health']
        pond_health_effect = params['pond_health_effect']
        stomach_health_effect = params['stomach_health_effect']
        
        pond = Pond(env=simpy.Environment(), id=1, type="Concrete_Pond", health=pond_health)
        fish = Fish(pond=pond, **fish_params)

        fish_pond_health_effect = round(fish.pond_health_effect(), 5)
        fish_stomach_health_effect = round(fish.stomach_health_effect(), 5)

        assert fish_pond_health_effect == pond_health_effect
        assert fish_stomach_health_effect == stomach_health_effect        
    
    @pytest.mark.parametrize("params", [
        [
            {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 50},
            {"id": 2, "type": "Catfish", "weight": 0.01, "stomach": 10}
        ],
        [
            {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 0},
            {"id": 2, "type": "Catfish", "weight": 0.02, "stomach": 50},
        ],
        [
            {"id": 1, "type": "Catfish", "weight": 0.01, "stomach": 0},
            {"id": 2, "type": "Catfish", "weight": 0.02, "stomach": 100},
        ]
    ])
    def test_existence(self, params):        
        pond = Pond(env=simpy.Environment(), id=1, type="Concrete_Pond")
        for p in params:
            Fish(pond=pond, **p)

        pond.env.run(1)
        fish_1 = pond.get_fish_by_id(1)
        fish_2 = pond.get_fish_by_id(2)

        assert fish_1.weight.level < fish_2.weight.level         