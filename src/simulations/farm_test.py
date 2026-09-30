import pytest
import simpy

from models.cycle import Phase, Stock
from models.farm import FarmBusinessModel
from models.pond import PondModel
from simulations.farm import Farm
from simulations.feed import Feed
from simulations.pond import Pond


class TestFarm():
    @pytest.mark.parametrize("params", [
        {"env": simpy.Environment(), "name": "Random", "money": 100_000},
        {"env": simpy.Environment(), "name": "Random", "money": 100_000_000},
    ])
    def test_create_farm(self, params):
        farm = Farm(**params)
        assert farm.name == params['name']
        assert farm.money.level == params['money']

    @pytest.mark.parametrize("params", [
        {},
        {"id": 1, "weight": 0.01},
        {"id": 1, "type": "Catfish"},
    ])
    def test_fail_create_invalid_farm(self, params):
        with pytest.raises(TypeError):
            Farm(**params)

    @pytest.mark.parametrize("params", [
        {
            "farm_params" : {"env": simpy.Environment(), "name": "Random", "money": 2000_00},
            "action": "debit",
            "amount": 1000_00,
            "balance": 1000_00
        },
        {
            "farm_params" : {"env": simpy.Environment(), "name": "Random", "money": 2000_00},
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
        transact_process = farm.transact(action, amount, "Random")
        next(transact_process)
        assert farm.money.level == balance

    @pytest.mark.parametrize("params", [
        {
            "farm_params" : {"env": simpy.Environment(), "name": "Random", "money": 100_000_00, "feeds": []},
            "weight": 1,
            "balance": 90_000_00
        },
        {
            "farm_params" : {"env": simpy.Environment(), "name": "Random", "money": 100_000_00, "feeds": []},
            "weight": 10,
            "balance": 0
        },
    ])
    def test_stock_feed(self, params):
        farm_params = params['farm_params']
        weight = params['weight']
        balance = params['balance']
        feed_size = 1

        farm = Farm(**farm_params)
        check_feed = farm.feed_exists(feed_size)
        assert check_feed == False

        feed = Feed(farm.env, "Random", feed_size)
        farm.env.process(farm.stock_feed(feed, weight))
        farm.env.run(1)

        check_feed = farm.feed_exists(feed_size)
        assert check_feed == True
        assert farm.money.level == balance

    @pytest.mark.parametrize("params", [
        {
            "farm_params" : {"name": "Random", "money": 100_000_00, "feeds": [], "ponds": []},
            "pond_params": {"id": 1, "type": "Portable_Pond"},
            "balance": 94_000_00,
            "until": 1,
            "num_ponds": 1
        },
        {
            "farm_params" : {"name": "Random", "money": 100_000_00, "feeds": [], "ponds": []},
            "pond_params": {"id": 1, "type": "Concrete_Pond", "duration": 365},
            "balance": 99_000_00,
            "until": 300,
            "num_ponds": 1
        },
        {
            "farm_params" : {"name": "Random", "money": 100_000_00, "feeds": [], "ponds": []},
            "pond_params": {"id": 1, "type": "Concrete_Pond", "duration": 365},
            "balance": 99_000_00,
            "until": 369,
            "num_ponds": 0
        },
    ])
    def test_acquire_pond(self, params):
        farm_params = params['farm_params']
        pond_params = params['pond_params']
        balance = params["balance"]
        until = params["until"]
        num_ponds = params["num_ponds"]

        env = simpy.Environment()
        farm = Farm(**{**farm_params, "env": env})
        pond = Pond(**{**pond_params, "env": env})

        env.process(farm.acquire_pond(pond))
        env.process(farm.pond_subscription())
        env.run(until)

        assert farm.money.level == balance
        assert len(farm.ponds) == num_ponds

    @pytest.mark.parametrize("params", [
        {
            "ponds_params" : [
                {"id": 1, "type": "Portable_Pond"},
                {"id": 2, "type": "Portable_Pond", "length": 2}
            ],
            "volume": 1,
            "pond_tag": "Portable_Pond_1",
        },
        {
            "ponds_params" : [
                {"id": 1, "type": "Portable_Pond"},
                {"id": 2, "type": "Portable_Pond", "length": 2, "width": 2}
            ],
            "volume": 1.5,
            "pond_tag": "Portable_Pond_2",
        },
    ])
    def test_available_pond(self, params):
        ponds_params = params['ponds_params']
        volume = params['volume']
        pond_tag = params['pond_tag']

        env = simpy.Environment()
        ponds: list[PondModel] = [
            Pond(**{**p, "env": env})
            for p in ponds_params
        ]
        farm = Farm(env, "Random", 1000_00, ponds=ponds)
        available_pond = farm.get_available_pond(volume)
        assert available_pond != None
        assert available_pond.tag == pond_tag

    @pytest.mark.parametrize("params", [
        {
            "business_model": FarmBusinessModel(
                stocks=[
                    Stock("Catfish", 10, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")])
                ]
            ),
            "money": 100_000_00,
            "until": 30,
            "n_cycles": 1,
            "last_stock_id": "Catfish_0",
            "balance": 90_000_00
        },
        {
            "business_model": FarmBusinessModel(
                stocks=[
                    Stock("Catfish", 10, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")])
                ]
            ),
            "money": 100_000_00,
            "until": 60,
            "n_cycles": 2,
            "last_stock_id": "Catfish_1",
            "balance": 90_000_00
        },
        {
            "business_model": FarmBusinessModel(
                stocks=[
                    Stock("Catfish", 10, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")]),
                    Stock("Catfish", 10, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")])
                ]
            ),
            "money": 100_000_00,
            "until": 60,
            "n_cycles": 2,
            "last_stock_id": "Catfish_1",
            "balance": 90_000_00
        },
        {
            "business_model": FarmBusinessModel(
                stocks=[
                    Stock("Catfish", 10, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")], gap=0),
                    Stock("Catfish", 20, "Small_Fingerlin", [Phase(30, [1], 1, "Juveniles")])
                ]
            ),
            "money": 100_000_00,
            "until": 60,
            "n_cycles": 4,
            "last_stock_id": "Catfish_3",
            "balance": 90_000_00
        },
    ])
    @pytest.mark.only
    def test_run_cycles(self, params):
        business_model = params['business_model']
        money = params['money']
        until = params['until']
        n_cycles = params['n_cycles']
        last_stock_id = params['last_stock_id']
        balance = params['balance']

        env = simpy.Environment()
        farm = Farm(env, "Random", money, ponds=[], feeds=[], business_model=business_model)

        env.process(farm.exist())
        env.run(until)

        n_farm_cycles = len(farm.cycles)
        assert n_cycles == n_farm_cycles

        last_cycle = farm.cycles[-1]
        assert last_cycle.stock.id == last_stock_id

        # assert farm.money.level == balance

    