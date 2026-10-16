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
            "health_level": 96.34, 
            "feed_level": 9, 
            "until": 10
        },
        {
            "pond_params": {"type": "Concrete_Pond", "length": 2, "width": 1, "depth": 1},
            "health_level": 99.37,
            "feed_level": 10.8, 
            "until": 10
        },
        {
            "pond_params": {"type": "Portable_Pond", "length": 2, "width": 20, "depth": 10},
            "health_level": 99.98,
            "feed_level": 7920, 
            "until": 100
        },
    ])
    def test_pond_existence(self, params):
        pond_params = params['pond_params']
        feed_level = params['feed_level']
        health_level = params['health_level']
        until = params['until']

        env = simpy.Environment()
        pond = Pond(env, id=1, **pond_params)
        pond.run(until)

        assert round(pond.health.level, 2) == health_level
        assert round(pond.feed.level, 2) == feed_level

    @pytest.mark.parametrize("params", [
        {
            "pond_params": {"type": "Earthen_Pond", "length": 1, "width": 1, "depth": 1}, 
            "pond_cost": 30_000_00, 
        },
        {
            "pond_params": {"type": "Concrete_Pond", "length": 1, "width": 2, "depth": 1}, 
            "pond_cost": 300_000_00, 
        },
        {
            "pond_params": {"type": "Portable_Pond", "length": 2, "width": 2, "depth": 1}, 
            "pond_cost": 240_000_00, 
        },
    ])
    def test_pond_cost(self, params):
        pond_params = params['pond_params']
        pond_cost = params['pond_cost']

        pond = Pond(env=simpy.Environment(), id=1, **pond_params)
        cost = pond.get_cost()
        assert cost == pond_cost

    @pytest.mark.parametrize("params", [
        {
            "pond_params": {"type": "Earthen_Pond", "length": 1, "width": 1, "depth": 1},
            "feed_level": 9, 
            "until": 10
        },
        {
            "pond_params": {"type": "Concrete_Pond", "length": 2, "width": 1, "depth": 1},
            "feed_level": 10.8, 
            "until": 10
        },
        {
            "pond_params": {"type": "Portable_Pond", "length": 2, "width": 20, "depth": 10},
            "feed_level": 720, 
            "until": 10
        },
    ])
    def test_spawn_feed(self, params):
        pond_params = params['pond_params']
        feed_level = params['feed_level']
        until = params['until']

        env = simpy.Environment()
        pond = Pond(env, id=1, **pond_params)
        pond.run(until)
        assert round(pond.feed.level, 5) == feed_level

    @pytest.mark.parametrize("params", [
        {
            "pond_params": {"type": "Earthen_Pond", "length": 1, "width": 1, "depth": 1},
            "health_level": 99.6, 
            "until": 2
        },
        {
            "pond_params": {"type": "Earthen_Pond", "length": 1, "width": 1, "depth": 1},
            "health_level": 96.34, 
            "until": 10
        },
        {
            "pond_params": {"type": "Concrete_Pond", "length": 2, "width": 1, "depth": 1},
            "health_level": 99.37, 
            "until": 10
        },
        {
            "pond_params": {"type": "Portable_Pond", "length": 7, "width": 1, "depth": 1},
            "health_level": 99.91, 
            "until": 10
        },
    ])
    def test_contaminate_pond(self, params):
        pond_params = params['pond_params']
        health_level = params['health_level']
        until = params['until']

        env = simpy.Environment()
        pond = Pond(env, id=1, **pond_params)
        pond.run(until)

        assert round(pond.health.level, 2) == health_level

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
        pond.run(until=until)

        health = pond.health.level
        assert pond.health.level < 100

        env.process(pond.decontaminate())
        extended_time = (until/2) + env.now
        env.run(extended_time)
        assert pond.health.level >= health
