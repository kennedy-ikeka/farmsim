import pytest
import simpy

from models.cycle import Phase, Stock
from simulations.cycle import Cycle
from simulations.farm import Farm
from simulations.fish import Fish

class TestCycle:
    @pytest.mark.parametrize("params", [
        {"id": 1},
        {"id": 100},
    ])
    def test_create_cycle(self, params):
        env = simpy.Environment()
        farm = Farm(env, "Random", 100_000_00, ponds=[], feeds=[])
        stock = Stock(id=1, type="Catfish", phases=[], size="Small_Fingerlin", count=1000)
        cycle = Cycle(env, farm, stock=stock, **params)
        assert cycle.tag == f"Cycle_{params['id']}"

    @pytest.mark.parametrize("params", [
        {},
    ])
    def test_fail_create_invalid_cycle(self, params):
        env = simpy.Environment()
        farm = Farm(env, "Random", 100_000_00, ponds=[], feeds=[])
        stock = Stock(id=1, type="Catfish", phases=[], size="Small_Fingerlin", count=1000)
        with pytest.raises(TypeError):
            Cycle(env, farm, stock=stock, **params)

    @pytest.mark.parametrize("params", [
        {
            "phases": [
                Phase(30, [1], 0, "Juveniles")
            ],
            "count": 10,
            "fish_size": "Small_Fingerlin",
            "until": 31,
            "money": 100_000_00,
            "n_batches": 1,
            "n_ponds": 1
        },
        {
            "phases": [
                Phase(30, [1], 0, "Juveniles"),
                Phase(30, [1], 0, "Juveniles")
            ],
            "count": 10,
            "fish_size": "Small_Fingerlin",
            "until": 70,
            "money": 100_000_00,
            "n_batches": 2,
            "n_ponds": 1
        },
        {
            "phases": [
                Phase(30, [1], 0, "Juveniles"),
                Phase(30, [1], 0, "Jumbo")
            ],
            "count": 10,
            "fish_size": "Small_Fingerlin",
            "until": 70,
            "money": 100_000_00,
            "n_batches": 2,
            "n_ponds": 2
        }
    ])
    def test_cycle_existence(self, params):
        phases = params['phases']
        count = params['count']
        fish_size = params['fish_size']
        until = params['until']
        n_batches = params['n_batches']
        n_ponds = params['n_ponds']
        money = params['money']
        
        env = simpy.Environment()
        farm = Farm(env, "Random", money=money, ponds=[], feeds=[], active=False)

        stock = Stock(id=1, type="Catfish", phases=phases, size=fish_size, count=count)
        cycle = Cycle(env, farm, stock=stock, id=1)
        cycle.run(until)

        assert len(cycle.batches) == n_batches
        assert len(farm.ponds) == n_ponds
        assert farm.money.level >= money

    @pytest.mark.parametrize("params", [
        {"fractions": [1], "count": 10},
        {"fractions": [.5, .5], "count": 10},
        {"fractions": [.2, .5, .3], "count": 10}
    ])
    def test_split_phase(self, params):
        fractions = params['fractions']
        count = params['count']

        env = simpy.Environment()
        farm = Farm(env, "Random", 100_000_00, ponds=[], feeds=[])

        phase = Phase(10, fractions, 1, "Medium_Fingerlin")
        stock = Stock(id=1, type="Catfish", phases=[phase], size="Small_Fingerlin", count=count)
        cycle = Cycle(env, farm, stock=stock, id=1)

        cycle.fishes = [Fish(farm.stocking_pond, i+1, stock.type, 40) for i in range(stock.count)]
        batches = cycle.split_phase(phase)
        assert len(batches) == len(phase.fractions)

        total_batch_length = sum([len(b) for b in batches])
        assert total_batch_length == len(cycle.fishes)

    @pytest.mark.parametrize("params", [
        {"duration": 10, "fractions": [1], "count": 10, "called_acquire_pond": 1},
        {"duration": 15, "fractions": [.5, .5], "count": 10, "called_acquire_pond": 2},
        {"duration": 10, "fractions": [.2, .5, .3], "count": 10, "called_acquire_pond": 3}
    ])
    def test_run_phases(self, params, monkeypatch):
        duration = params['duration']
        fractions = params['fractions']
        count = params['count']
        called_acquire_pond = params['called_acquire_pond']

        env = simpy.Environment()
        called = {"acquire_pond": 0}
        def fake_acquire_pond(self, pond):
            called['acquire_pond'] += 1
            yield env.timeout(0)

        monkeypatch.setattr(Farm, "acquire_pond", fake_acquire_pond)
        farm = Farm(env, "Random", 100_000_00, ponds=[], feeds=[], active=False)

        phase = Phase(duration, fractions, 1, "Medium_Fingerlin")
        stock = Stock(id=1, type="Catfish", phases=[phase], size="Small_Fingerlin", count=count)
        cycle = Cycle(env, farm, stock=stock, id=1, active=False)

        cycle.fishes = [Fish(farm.stocking_pond, i+1, stock.type, 40) for i in range(stock.count)]
        env.process(cycle.run_next_phase())
        env.run(duration)

        assert called_acquire_pond == called['acquire_pond']
       
    @pytest.mark.parametrize("params", [
        {"fish_size": "Fry", "count": 10, "called_transaction_amount": 25_00},
        {"fish_size": "Small_Fingerlin", "count": 10, "called_transaction_amount": 2_500_00},
        {"fish_size": "Medium_Fingerlin", "count": 10, "called_transaction_amount": 750_00}
    ])
    def test_stock_fishes(self, params, monkeypatch):
        fish_size = params['fish_size']
        count = params['count']
        called_transaction_amount = params['called_transaction_amount']

        env = simpy.Environment()
        called = {"called_transaction_amount": 0, "called_transaction_quantity": 0}
        def fake_transact(self, action, amount, item, entity_tag, quantity):
            if action == 'debit' and item == 'fishes':
                called['called_transaction_amount'] = amount
                called['called_transaction_quantity'] = quantity
            yield env.timeout(0)

        monkeypatch.setattr(Farm, "transact", fake_transact)
        farm = Farm(env, "Random", 100_000_00, ponds=[], feeds=[], active=False)

        phase = Phase(10, [1], 1, "Medium_Fingerlin")
        stock = Stock(id=1, type="Catfish", phases=[phase], size=fish_size, count=count)
        cycle = Cycle(env, farm, stock=stock, id=1, active=False)

        env.process(cycle.stock_fishes())
        env.run(.1)

        assert called["called_transaction_amount"] <= called_transaction_amount
        assert called["called_transaction_quantity"] == count
        assert len(cycle.fishes) == count

    @pytest.mark.parametrize("params", [
        {"fish_size": 40, "harvest_rate": 0, "count": 10, "called_transaction_amount": 0, "called_transaction_quantity": 0},
        {"fish_size": 1000, "harvest_rate": 1, "count": 10, "called_transaction_amount": 25_000_00, "called_transaction_quantity": 10},
        {"fish_size": 2000, "harvest_rate": .5, "count": 10, "called_transaction_amount": 25_000_00, "called_transaction_quantity": 5}
    ])
    def test_harvest_fishes(self, params, monkeypatch):
        fish_size = params['fish_size']
        count = params['count']
        harvest_rate = params['harvest_rate']
        called_transaction_amount = params['called_transaction_amount']
        called_transaction_quantity = params['called_transaction_quantity']

        env = simpy.Environment()
        called = {"called_transaction_amount": 0, "called_transaction_quantity": 0}
        def fake_transact(self, action, amount, item, entity_tag, quantity):
            if action == 'credit' and item == 'fishes':
                called['called_transaction_amount'] = amount
                called['called_transaction_quantity'] = quantity
            yield env.timeout(0)

        monkeypatch.setattr(Farm, "transact", fake_transact)
        farm = Farm(env, "Random", money=100_000_000_00, ponds=[], feeds=[], active=False)

        phase = Phase(10, [1], 1, "Medium_Fingerlin")
        stock = Stock(id=1, type="Catfish", phases=[phase], size="Small_Fingerlin", count=count)
        cycle = Cycle(env, farm, stock=stock, id=1, active=False)

        cycle.next_harvest_rate = harvest_rate
        cycle.fishes = [Fish(farm.stocking_pond, i+1, stock.type, fish_size) for i in range(stock.count)]
        env.process(cycle.harvest_fishes())
        env.run(1)

        assert called["called_transaction_amount"] == called_transaction_amount
        assert called["called_transaction_quantity"] == called_transaction_quantity
        assert len(cycle.fishes) == count - called_transaction_quantity
