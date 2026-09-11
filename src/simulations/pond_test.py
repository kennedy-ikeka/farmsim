import pytest
import simpy

from src.simulations.pond import Pond


class TestPond():
    @pytest.mark.parametrize("params", [
        {"env": simpy.Environment(), "id": 1, "type": "Earthen_Pond"},
        {"env": simpy.Environment(), "id": 1, "type": "Earthen_Pond", "length": 2, "width": 2, "depth": 1},
        {"env": simpy.Environment(), "id": 1, "type": "Earthen_Pond", "density": 1.5}
    ])
    def test_create_pond(self, params):
        pond = Pond(**params)
        assert pond.id == 1
        assert pond.tag == f'Earthen_Pond_1'

    @pytest.mark.parametrize("params", [
        {},
        {"env": simpy.Environment(), "length": 2, "width": 2, "depth": 1},
        {"env": simpy.Environment(), "id": 1}
    ])
    def test_fail_create_invalid_pond(self, params):
        with pytest.raises(TypeError):
            Pond(**params)

    @pytest.mark.parametrize("params", [
        {
            "pond_params": {"type": "Earthen_Pond", "length": 1, "width": 1, "depth": 1}, 
            "pond_cost": 1_500, 
            "pond_rental_cost": 150
        },
        {
            "pond_params": {"type": "Concrete_Pond", "length": 1, "width": 2, "depth": 1}, 
            "pond_cost": 12_000, 
            "pond_rental_cost": 1_200
        },
        {
            "pond_params": {"type": "Portable_Pond", "length": 2, "width": 2, "depth": 1}, 
            "pond_cost": 16_000, 
            "pond_rental_cost": 1_600
        },
    ])
    def test_pond_cost(self, params):
        pond_params = params['pond_params']
        pond_cost = params['pond_cost']
        pond_rental_cost = params['pond_rental_cost']

        pond = Pond(env=simpy.Environment(), id=1, **pond_params)
        cost = pond.get_cost()
        assert cost == pond_cost

        rental_cost = pond.get_rent_cost()
        assert rental_cost == pond_rental_cost

    @pytest.mark.parametrize("params", [
        {
            "pond_params": {"type": "Earthen_Pond", "length": 1, "width": 1, "depth": 1},
            "feed_level": 0.1, 
        },
        {
            "pond_params": {"type": "Concrete_Pond", "length": 2, "width": 1, "depth": 1},
            "feed_level": .12, 
        },
        {
            "pond_params": {"type": "Portable_Pond", "length": 2, "width": 20, "depth": 10},
            "feed_level": 8, 
        },
    ])
    def test_spawn_feed(self, params):
        pond_params = params['pond_params']
        feed_level = params['feed_level']

        pond = Pond(env=simpy.Environment(), id=1, **pond_params)
        process = pond.spawn_feed()
        next(process)
        next(process)
        assert pond.feed.level == feed_level

    @pytest.mark.parametrize("params", [
        {
            "pond_params": {"type": "Earthen_Pond", "length": 1, "width": 1, "depth": 1},
            "health_level": 99.6, 
        },
        {
            "pond_params": {"type": "Concrete_Pond", "length": 2, "width": 1, "depth": 1},
            "health_level": 99.925, 
        },
        {
            "pond_params": {"type": "Portable_Pond", "length": 7, "width": 1, "depth": 1},
            "health_level": 99.99, 
        },
    ])
    def test_contaminate_pond(self, params):
        pond_params = params['pond_params']
        health_level = params['health_level']

        pond = Pond(env=simpy.Environment(), id=1, **pond_params)
        process = pond.contaminate()
        next(process)
        next(process)
        assert pond.health.level == health_level

    @pytest.mark.parametrize("params", [
        {
            "pond_params": {"type": "Earthen_Pond", "length": 1, "width": 1, "depth": 1},
            "until": 5,
        },
        {
            "pond_params": {"type": "Concrete_Pond", "length": 2, "width": 1, "depth": 1},
            "until": 10,
        },
        {
            "pond_params": {"type": "Portable_Pond", "length": 7, "width": 1, "depth": 1},
            "until": 100,
        },
    ])
    def test_decontaminate_pond(self, params):
        pond_params = params['pond_params']
        until = params['until']

        env=simpy.Environment()
        pond = Pond(env=env, id=1, **pond_params)
        env.run(until=until)

        health = pond.health.level
        assert pond.health.level < 100

        env.process(pond.decontaminate())
        extended_time = (until/2) + env.now
        env.run(extended_time)
        assert pond.health.level >= health
