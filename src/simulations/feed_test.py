import pytest
import simpy

from src.simulations.feed import Feed

@pytest.mark.only
class TestFeed:
    @pytest.mark.parametrize("params", [
        {"env": simpy.Environment(), "name": "Random", "size": 1.0},
        {"env": simpy.Environment(), "name": "Random", "size": 1.0, "sinks": False},
        {"env": simpy.Environment(), "name": "Random", "size": 1.0, "sinks": True, "rate": .9}
    ])
    def test_create_feed(self, params):
        feed = Feed(**params)
        assert feed.name == 'Random'
        assert feed.tag == f'Random_1.0'

    @pytest.mark.parametrize("params", [
        {},
        {"env": simpy.Environment()}
    ])
    def test_fail_create_invalid_feed(self, params):
        with pytest.raises(TypeError):
            Feed(**params)

    @pytest.mark.parametrize("params", [
        [10],
        [10, 10],
    ])
    def test_refiil_feed(self, params):
        feed = Feed(env=simpy.Environment(), name="Random", size=1.0)       
        for i in params:
            feed.refill(i)

        q = feed.get_quantity()
        assert q == sum(params)

    @pytest.mark.parametrize("params", [
        [10],
        [10, 10],
    ])
    def test_consume_feed(self, params):
        feed = Feed(env=simpy.Environment(), name="Random", size=1.0)
        feed.refill(100)

        for i in params:
            c = feed.consume(i)
            next(c)

        q = feed.get_quantity()
        assert q == 100 - sum(params)

    @pytest.mark.parametrize("params", [
        10,
        80,
        90,
        100
    ])
    def test_expire_feed(self, params):
        env = simpy.Environment()
        feed = Feed(env=env, name="Random", size=1.0)
        feed.refill(10)
        env.run(until=params)

        if params > 90:
            assert len(feed.batches) == 0
        else:
            assert len(feed.batches) == 1

    @pytest.mark.parametrize("params", [
        {"feed_params": {"size": 1.0}, "weight": 1, "feed_cost": 10000},
        {"feed_params": {"size": 0.8}, "weight": 1, "feed_cost": 12500},
        {"feed_params": {"size": 1, "sinks": True}, "weight": 1, "feed_cost": 8000},
        {"feed_params": {"size": 1, "rate": .8}, "weight": 1, "feed_cost": 8000}
    ])
    def test_feed_cost(self, params):
        feed_params = params['feed_params']
        weight = params['weight']
        feed_cost = params["feed_cost"]

        env = simpy.Environment()
        feed = Feed(env=env, name="Random", **feed_params)
        cost = feed.get_cost(weight)
        assert cost == feed_cost
        