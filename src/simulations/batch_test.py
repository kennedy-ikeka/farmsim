from pydantic import ValidationError
import pytest
import numpy as np

import warnings
warnings.simplefilter("error", RuntimeWarning)

from src.models.feed import FeedModel
from src.simulations.batch import Batch
from src.simulations.farm import Farm
from src.simulations.feed import Feed
from src.simulations.fish import Fish
from src.simulations.pond import Pond
from src.simulations.simulation import Simulation

class TestBatch:    
    @pytest.mark.parametrize("params", [
        {"id": "1", "duration": 1, "cycle_id": "0"},
        {"id": "1", "duration": 10, "cycle_id": "10"},
    ])
    def test_create_batch(self, params):
        sim = Simulation()
        pond = Pond(sim=sim, type="Portable_Pond")
        farm = Farm(sim=sim, name="Random", pond_ids=[pond.id])
        fish = Fish(sim=sim, pond_id=pond.id, type="Catfish", options={"weight": 40})

        batch = Batch(sim=sim, farm_id=farm.id, pond_id=pond.id, fish_ids=[fish.id], **params)
        assert batch.tag == "Batch_1"
        assert batch.active == True
        assert batch.duration == params['duration']

    @pytest.mark.parametrize("params", [
        {},
        {"duration": 1},
        {"duration": 0, "cycle_id": "0"},
    ])
    def test_fail_create_invalid_batch(self, params):
        with pytest.raises(ValidationError):
            Batch(**params)

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "until": 1,
            "t_next_feeding": 7
        },
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "until": 1.5,
            "t_next_feeding": 7
        },
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "until": 1.875,
            "t_next_feeding": 10
        }
    ])
    def test_get_next_feeding_time(self, params):
        batch_params = params["batch_params"]
        until = params["until"]
        t_next_feeding = params["t_next_feeding"]

        sim = Simulation()
        pond = Pond(sim=sim, type="Portable_Pond")
        farm = Farm(sim=sim, name="Random", pond_ids=[pond.id], active=False)
        fish = Fish(sim=sim, pond_id=pond.id, type="Catfish", options={"weight": 40})

        batch = Batch(sim=sim, farm_id=farm.id, pond_id=pond.id, fish_ids=[fish.id], **batch_params)
        batch.run(until)

        n_feeding_time = round(batch.get_next_feeding_time() * 24)
        # assert n_feeding_time == t_next_feeding

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "fish_size": 40,
            "feed_size": 1.5
        },
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "fish_size": 99,
            "feed_size": 2
        },
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "fish_size": 2100,
            "feed_size": 6
        },
    ])    
    def test_get_feed_size(self, params):
        batch_params = params["batch_params"]
        fish_size = params["fish_size"]
        feed_size = params["feed_size"]

        sim = Simulation()
        pond = Pond(sim=sim, type="Portable_Pond")
        farm = Farm(sim=sim, name="Random", pond_ids=[pond.id], active=False)
        fish = Fish(sim=sim, pond_id=pond.id, type="Catfish", options={"weight": fish_size})
        batch = Batch(sim=sim, farm_id=farm.id, pond_id=pond.id, fish_ids=[fish.id], **batch_params)

        batch_feed_size = batch.get_feed_size()
        assert batch_feed_size == feed_size

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "fish_size": 40,
            "feeds_params": [],
            "available_feed": False
        },
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "fish_size": 40,
            "feeds_params": [{"name": "Random", "size": 1.5}],
            "available_feed": True
        },
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
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

        sim = Simulation()
        feeds: list[str] = [Feed(**f, sim=sim).id for f in feeds_params]
        pond = Pond(sim=sim, type="Portable_Pond")
        farm = Farm(sim=sim, name="Random", pond_ids=[pond.id], feed_ids=feeds, active=False)
        fish = Fish(sim=sim, pond_id=pond.id, type="Catfish", options={"weight": fish_size})
        batch = Batch(sim=sim, farm_id=farm.id, pond_id=pond.id, fish_ids=[fish.id], **batch_params)

        batch_feed = batch.get_feed()
        assert (batch_feed is not None) == available_feed

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "t_next_feeding": .1,
            "fish_size": 40,
        },
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "t_next_feeding": .3,
            "fish_size": 40,
        },
    ])
    def test_feed_fishes(self, params, monkeypatch):
        batch_params = params["batch_params"]
        t_next_feeding = params["t_next_feeding"]
        fish_size = params["fish_size"]

        sim = Simulation()
        feed = Feed(sim=sim, farm_id="1", name="Random", size=1)
        pond = Pond(sim=sim, type="Portable_Pond")
        farm = Farm(sim=sim, id="1", name="Random", pond_ids=[pond.id], feed_ids=[feed.id], active=False)
        fish = Fish(sim=sim, pond_id=pond.id, type="Catfish", options={"weight": fish_size})

        called = {"stocked_feed": 0, "consumed_feed": 0}
        def fake_stock_feed(self, feed, weight):
            called["stocked_feed"] += weight
            yield farm.env.timeout(0)
        monkeypatch.setattr(Farm, "stock_feed", fake_stock_feed)

        def fake_feed_consume(self, weight):
                called["consumed_feed"] += weight
                yield feed.env.timeout(0)
        monkeypatch.setattr(Feed, "consume", fake_feed_consume)

        batch = Batch(sim=sim, farm_id=farm.id, pond_id=pond.id, fish_ids=[fish.id], **batch_params)
        batch.schedules['next_feeding'] = t_next_feeding
        sim.env.process(batch.feed_fishes())
        sim.env.run(until=t_next_feeding + 1)

        assert called["consumed_feed"] > 0 
        assert called["stocked_feed"] > 0

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "pond_health": 40,
            "decontamination_called": True
        },
        {
            "batch_params": {"duration": 1, "cycle_id": "0"},
            "pond_health": 90,
            "decontamination_called": False
        },
    ])
    def test_maintain_pond(self, params, monkeypatch):
        batch_params = params["batch_params"]
        pond_health = params["pond_health"]
        decontamination_called = params["decontamination_called"]

        sim = Simulation()
        pond = Pond(sim=sim, type="Portable_Pond", options={"health": pond_health})
        farm = Farm(sim=sim, name="Random", pond_ids=[pond.id], active=False)
        fish = Fish(sim=sim, pond_id=pond.id, type="Catfish", options={"weight": 40})

        called = {"decontaminated": False}
        def fake_decontamination(self):
            called["decontaminated"] = True
            yield pond.env.timeout(0)
        monkeypatch.setattr(Pond, "decontaminate", fake_decontamination)

        batch = Batch(sim=sim, farm_id=farm.id, pond_id=pond.id, fish_ids=[fish.id], **batch_params)
        batch.run(until=2)

        assert called["decontaminated"] == decontamination_called

    @pytest.mark.parametrize("params", [
        {
            "batch_params": {"duration": 10, "cycle_id": "0"},
            "until": 20,
            "fish_size": 40,
            "active": False
        },
        {
            "batch_params": {"duration": 100, "cycle_id": "0"},
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

        sim = Simulation()
        pond = Pond(sim=sim, type="Portable_Pond")
        farm = Farm(sim=sim, name="Random", pond_ids=[pond.id], active=False)
        fish = Fish(sim=sim, pond_id=pond.id, type="Catfish", options={"weight": 40})
        batch = Batch(sim=sim, farm_id=farm.id, pond_id=pond.id, fish_ids=[fish.id], **batch_params)
        sim.env.run(until)

        median_fish_size = np.median([f.containers['weight'].level for f in batch.fishes])
        assert median_fish_size > fish_size
        assert batch.get_age() == until
        assert batch.active == active
