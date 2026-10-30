from pydantic import ValidationError
import pytest
import simpy

from src.simulations.simulation import Simulation
from src.models.cycle import Phase, Stock
from src.models.farm import FarmBusinessModel
from src.models.pond import PondModel
from src.simulations.farm import Farm
from src.simulations.feed import Feed
from src.simulations.pond import Pond

class TestFarm():
    @pytest.mark.parametrize("params", [
        {"id": "1", "name": "Random", },
        {"id": "1", "name": "Great"},
    ])
    def test_create_farm(self, params):
        farm = Farm(**params)
        assert farm.name == params['name']

    @pytest.mark.parametrize("params", [
        {},
        {"id": "1", "weight": 0.01},
        {"id": "1", "type": "Catfish"},
    ])
    def test_fail_create_invalid_farm(self, params):
        with pytest.raises(ValidationError):
            Farm(**params)

    @pytest.mark.parametrize("params", [
        {
            "capital": 100_000_00,
            "gap": None,
            "stock_count": 1,
            "duration": 30,
            "until": 32,
            "n_cycles": 2,
            "last_stock_id": 1,
        },
        {
            "capital": 100_000_00,
            "gap": None,
            "duration": 30,
            "stock_count": 1,
            "until": 70,
            "n_cycles": 3,
            "last_stock_id": 1,
        },
        {
            "capital": 100_000_00,
            "gap": None,
            "duration": 30,
            "stock_count": 2,
            "until": 60,
            "n_cycles": 2,
            "last_stock_id": 2,
        },
        {
            "capital": 1_000_000_00,
            "gap": 0,
            "duration": 30,
            "stock_count": 2,
            "until": 60,
            "n_cycles": 4,
            "last_stock_id": 2,
        },
    ])
    def test_farm_existence(self, params):
        capital = params['capital']
        gap = params['gap']
        duration = params['duration']
        stock_count = params['stock_count']
        until = params['until']
        n_cycles = params['n_cycles']
        last_stock_id = params['last_stock_id']

        stocks = [
            Stock(id, "Catfish", 10, "Small_Fingerlin", [Phase(duration, [1], 1, "Juveniles")], gap=gap)
            for id in range(1, stock_count+1)
        ]

        sim = Simulation()
        farm = Farm(sim=sim, name="Random", ponds=[], feeds=[], business_model=FarmBusinessModel(stocks=stocks, capital=capital))
        farm.env.run(until)

        n_farm_cycles = len(farm.cycles)
        assert n_cycles == n_farm_cycles

        last_cycle = farm.cycles[-1]
        assert last_cycle.stock.id == last_stock_id

    @pytest.mark.parametrize("params", [
        {
            "farm_params" : {"name": "Random", "business_model": FarmBusinessModel(capital=2_000_00)},
            "action": "debit",
            "amount": 1000_00,
            "balance": 1000_00
        },
        {
            "farm_params" : {"name": "Random", "business_model": FarmBusinessModel(capital=2_000_00)},
            "action": "credit",
            "amount": 1000_00,
            "balance": 3000_00
        },
    ])
    def test_transact(self, params):
        farm_params = params['farm_params']
        action = params['action']
        amount = params['amount']
        balance = params['balance']

        farm = Farm(**farm_params)
        transact_process = farm.transact(action, amount, "Random", farm.tag)
        next(transact_process)
        next(transact_process)
        assert farm.containers['money'].level == balance

    @pytest.mark.parametrize("params", [
        {
            "farm_params" : {"name": "Random", "business_model": FarmBusinessModel(capital=100_000_00), "feeds": []},
            "weight": 1000,
            "balance": 90_000_00
        },
        {
            "farm_params" : {"name": "Random", "business_model": FarmBusinessModel(capital=100_000_00), "feeds": []},
            "weight": 10000,
            "balance": 0
        },
    ])
    def test_stock_feed(self, params):
        farm_params = params['farm_params']
        weight = params['weight']
        balance = params['balance']
        feed_size = 1

        sim = Simulation()
        farm = Farm(sim=sim, **farm_params, active=False)
        check_feed = farm.feed_exists(feed_size)
        assert check_feed == False

        feed = Feed(sim=sim, name="Random", size=feed_size)
        farm.env.process(farm.stock_feed(feed, weight))
        farm.env.run(1)

        check_feed = farm.feed_exists(feed_size)
        assert check_feed == True
        assert farm.containers['money'].level == balance

    @pytest.mark.parametrize("params", [
        {
            "farm_params" : {"name": "Random", "business_model": FarmBusinessModel(capital=100_000_00), "feeds": [], "ponds": []},
            "pond_params": {"type": "Portable_Pond"},
            "balance": 40_000_00,
            "until": 1,
            "num_ponds": 1
        },
        {
            "farm_params" : {"name": "Random", "business_model": FarmBusinessModel(capital=100_000_00), "feeds": [], "ponds": []},
            "pond_params": {"type": "Concrete_Pond", "duration": 2},
            "balance": 70_000_00,
            "until": 15,
            "num_ponds": 1
        },
        {
            "farm_params" : {"name": "Random", "business_model": FarmBusinessModel(capital=100_000_00), "feeds": [], "ponds": []},
            "pond_params": {"type": "Concrete_Pond", "duration": 1},
            "balance": 85_000_00,
            "until": 36,
            "num_ponds": 1
        },
    ])
    def test_acquire_pond(self, params):
        farm_params = params['farm_params']
        pond_params = params['pond_params']
        balance = params["balance"]
        until = params["until"]
        num_ponds = params["num_ponds"]

        sim = Simulation()
        farm = Farm(sim=sim, **farm_params, active=False)
        pond = Pond(sim=sim, **pond_params)

        farm.env.process(farm.acquire_pond(pond))
        farm.env.process(farm.pond_subscription())
        farm.env.run(until)

        assert farm.containers["money"].level == balance
        assert len(farm.ponds) == num_ponds

    @pytest.mark.parametrize("params", [
        {
            "ponds_params" : [
                {"id": "1", "type": "Portable_Pond"},
                {"id": "2", "type": "Portable_Pond", "length": 2}
            ],
            "volume": 1,
            "pond_tag": "Pond_1",
        },
        {
            "ponds_params" : [
                {"id": "1", "type": "Portable_Pond"},
                {"id": "2", "type": "Portable_Pond", "length": 2, "width": 2}
            ],
            "volume": 1.5,
            "pond_tag": "Pond_2",
        },
    ])
    def test_available_pond(self, params):
        ponds_params = params['ponds_params']
        volume = params['volume']
        pond_tag = params['pond_tag']

        sim = Simulation()
        ponds: list[PondModel] = [
            Pond(sim=sim, **p)
            for p in ponds_params
        ]
        farm = Farm(sim=sim, name="Random", ponds=ponds)
        available_pond = farm.get_available_pond(volume)
        assert available_pond != None
        assert available_pond.tag == pond_tag

    @pytest.mark.parametrize("params", [
        {
            "business_model": FarmBusinessModel(stocks=[Stock(1, "Catfish", 10, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")])]),
            "until": 31,
            "n_cycles": 1,
            "last_stock_id": 1,
        },
        {
            "business_model": FarmBusinessModel(
                stocks=[
                    Stock(2, "Catfish", 10, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")]),
                    Stock(1, "Catfish", 10, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")]),
                ]
            ),
            "until": 60,
            "n_cycles": 1,
            "last_stock_id": 2,
        },
        {
            "business_model": FarmBusinessModel(
                stocks=[
                    Stock(1, "Catfish", 10, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")], gap=0),
                    Stock(2, "Catfish", 20, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")])
                ]
            ),
            "until": 60,
            "n_cycles": 1,
            "last_stock_id": 1,
        },
        {
            "business_model": FarmBusinessModel(
                stocks=[
                    Stock(1, "Catfish", 10, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")], gap=0),
                ]
            ),
            "until": 60,
            "n_cycles": 1,
            "last_stock_id": 1,
        },
    ])
    def test_run_next_cycle(self, params):
        business_model = params['business_model']
        until = params['until']
        n_cycles = params['n_cycles']
        last_stock_id = params['last_stock_id']

        env = simpy.Environment()
        farm = Farm(name="Random", ponds=[], feeds=[], business_model=business_model, active=False)

        env.process(farm.run_next_cycle(True))
        env.run(until)

        n_farm_cycles = len(farm.cycles)
        assert n_cycles == n_farm_cycles

        last_cycle = farm.cycles[-1]
        assert last_cycle.stock.id == last_stock_id

        assert farm.containers['money'].level >= business_model.capital
    