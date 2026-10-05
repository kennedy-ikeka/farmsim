import pytest
import simpy
import numpy as np

from models.cycle import Phase, Stock
from models.feed import FeedModel
from simulations.batch import Batch
from simulations.farm import Farm
from simulations.feed import Feed
from simulations.fish import Fish
from simulations.pond import Pond


class TestBatch:
    @pytest.mark.parametrize("params", [
        {"duration": 1, "stock_id": "Catfish_0"},
        {"duration": 10, "stock_id": "Catfish_10"},
    ])
    def test_create_batch(self, params):
        env = simpy.Environment()
        pond = Pond(env=env, id=1, type="Portable_Pond")
        farm = Farm(env, "Random", 100_000_00, ponds=[pond], feeds=[])
        fish = Fish(pond, 1, "Catfish", 40)

        batch = Batch(farm, pond, [fish], **params)
        assert batch.tag == f"{pond.tag}_{params['stock_id']}"
        assert batch.active == True
        assert batch.duration == params['duration']

    @pytest.mark.parametrize("params", [
        {},
        {"duration": 1},
        {"duration": 0, "stock_id": "Catfish_0"},
    ])
    def test_fail_create_invalid_batch(self, params):
        with pytest.raises(TypeError):
            Batch(**params)

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "until": 1,
            "t_next_feeding": 7
        },
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "until": 1.5,
            "t_next_feeding": 7
        },
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "until": 1.875,
            "t_next_feeding": 10
        }
    ])
    def test_get_next_feeding_time(self, params):
        batch_params = params["batch_params"]
        until = params["until"]
        t_next_feeding = params["t_next_feeding"]

        env = simpy.Environment()
        pond = Pond(env=env, id=1, type="Portable_Pond")
        farm = Farm(env, "Random", 100_000_00, ponds=[pond], feeds=[])
        fish = Fish(pond, 1, "Catfish", 40)

        batch = Batch(farm, pond, [fish], **batch_params)
        batch.run(until)

        n_feeding_time = round(batch.get_next_feeding_time() * 24)
        assert n_feeding_time == t_next_feeding

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "fish_size": 40,
            "feed_size": 1.5
        },
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "fish_size": 99,
            "feed_size": 2
        },
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "fish_size": 2100,
            "feed_size": 6
        },
    ])
    def test_get_feed_size(self, params):
        batch_params = params["batch_params"]
        fish_size = params["fish_size"]
        feed_size = params["feed_size"]

        env = simpy.Environment()
        pond = Pond(env=env, id=1, type="Portable_Pond")
        farm = Farm(env, "Random", 100_000_00, ponds=[pond], feeds=[])
        fish = Fish(pond, 1, "Catfish", fish_size)

        batch = Batch(farm, pond, [fish], **batch_params)
        batch_feed_size = batch.get_feed_size()
        assert batch_feed_size == feed_size

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "fish_size": 40,
            "feeds_params": [],
            "available_feed": False
        },
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "fish_size": 40,
            "feeds_params": [{"name": "Random", "size": 1.5}],
            "available_feed": True
        },
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "fish_size": 40,
            "feeds_params": [{"name": "Random", "size": 6}],
            "available_feed": False
        },
    ])
    def test_get_feed(self, params):
        batch_params = params["batch_params"]
        fish_size = params["fish_size"]
        feeds_params = params["feeds_params"]
        available_feed = params["available_feed"]

        env = simpy.Environment()
        pond = Pond(env=env, id=1, type="Portable_Pond")
        feeds: list[FeedModel] = [Feed(**{**f, "env": env}) for f in feeds_params]
        farm = Farm(env, "Random", 100_000_00, ponds=[pond], feeds=feeds)
        fish = Fish(pond, 1, "Catfish", fish_size)

        batch = Batch(farm, pond, [fish], **batch_params)
        batch_feed = batch.get_feed()
        assert (batch_feed is not None) == available_feed

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "t_next_feeding": .1,
            "fish_size": 40,
        },
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "t_next_feeding": .3,
            "fish_size": 40,
        },
    ])
    def test_feed_fishes(self, params, monkeypatch):
        batch_params = params["batch_params"]
        t_next_feeding = params["t_next_feeding"]
        fish_size = params["fish_size"]

        env = simpy.Environment()
        pond = Pond(env=env, id=1, type="Portable_Pond")
        feed = Feed(env=env, name="Random", size=1)
        farm = Farm(env, "Random", 100_000_00, ponds=[pond], feeds=[feed])
        fish = Fish(pond, 1, "Catfish", fish_size)

        called = {"stocked_feed": 0, "consumed_feed": 0}
        def fake_stock_feed(self, feed, weight):
            called["stocked_feed"] += weight
            yield env.timeout(0)
        monkeypatch.setattr(Farm, "stock_feed", fake_stock_feed)

        def fake_feed_consume(self, total_feed_kilos):
                called["consumed_feed"] += total_feed_kilos
                yield env.timeout(0)
        monkeypatch.setattr(Feed, "consume", fake_feed_consume)

        batch = Batch(farm, pond, [fish], **batch_params)
        batch.t_next_feeding = t_next_feeding
        env.process(batch.feed_fishes())
        env.run(until=batch.t_next_feeding + 1)

        assert called["consumed_feed"] > 0 
        assert called["stocked_feed"] > 0

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "pond_health": 40,
            "decontamination_called": True
        },
        {
            "batch_params": {"duration": 1, "stock_id": "Catfish_0"},
            "pond_health": 60,
            "decontamination_called": False
        },
    ])
    def test_maintain_pond(self, params, monkeypatch):
        batch_params = params["batch_params"]
        pond_health = params["pond_health"]
        decontamination_called = params["decontamination_called"]

        env = simpy.Environment()
        pond = Pond(env=env, id=1, type="Portable_Pond", health=pond_health)
        farm = Farm(env, "Random", 100_000_00, ponds=[pond], feeds=[])
        fish = Fish(pond, 1, "Catfish", 40)

        called = {"decontaminated": False}
        def fake_decontamination(self):
            called["decontaminated"] = True
            yield env.timeout(0)
        monkeypatch.setattr(Pond, "decontaminate", fake_decontamination)

        batch = Batch(farm, pond, [fish], **batch_params)
        env.process(batch.maintain_pond())
        env.run(until=1)

        assert called["decontaminated"] == decontamination_called

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 10, "stock_id": "Catfish_0"},
            "until": 100,
            "fish_size": 40,
            "active": False
        },
        {
            "batch_params": {"duration": 100, "stock_id": "Catfish_0"},
            "until": 10,
            "fish_size": 40,
            "active": True
        },
    ])
    def test_batch_existence(self, params):
        batch_params = params["batch_params"]
        until = params["until"]
        fish_size = params["fish_size"]
        active = params["active"]

        env = simpy.Environment()
        pond = Pond(env=env, id=1, type="Portable_Pond")
        farm = Farm(env, "Random", 100_000_00, ponds=[pond], feeds=[])
        fish = Fish(pond, 1, "Catfish", fish_size)

        batch = Batch(farm, pond, [fish], **batch_params)
        batch.run(until)

        median_fish_size = np.median([f.weight.level for f in batch.fishes])
        assert median_fish_size > fish_size
        assert batch.get_age() == until
        assert batch.active == active
