import pytest
import simpy

from src.simulations.feed import Feed

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
        {"refill": 10, "consume": 10, "until": 10, "left": 0},
        {"refill": 10, "consume": 5, "until": 10, "left": 5},
        {"refill": 10, "consume": 15, "until": 10, "left": 0},
        {"refill": 10, "consume": 0, "until": 10, "left": 10},
        {"refill": 10, "consume": 5, "until": 100, "left": 0},
    ])
    def test_feed_existence(self, params):
        refill = params['refill']
        consume = params['consume']
        until = params['until']
        left = params['left']

        env = simpy.Environment()
        feed = Feed(env, name="Random", size=1.0)   

        feed.refill(refill)
        env.process(feed.consume(consume))
        env.run(until=until)

        q = feed.get_quantity()
        assert q == left


    @pytest.mark.parametrize("params", [
        [10],
        [10, 10],
        [10, 10000],
    ])
    def test_refill_feed(self, params):
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
        {"feed_params": {"size": 1.0}, "weight": 1000, "feed_cost": 10000_00},
        {"feed_params": {"size": 0.8}, "weight": 1000, "feed_cost": 12500_00},
        {"feed_params": {"size": 1, "sinks": True}, "weight": 1000, "feed_cost": 8000_00},
        {"feed_params": {"size": 1, "rate": .8}, "weight": 1000, "feed_cost": 8000_00}
    ])
    def test_feed_cost(self, params):
        feed_params = params['feed_params']
        weight = params['weight']
        feed_cost = params["feed_cost"]

        env = simpy.Environment()
        feed = Feed(env=env, name="Random", **feed_params)
        cost = feed.get_cost(weight)
        assert cost == feed_cost
        