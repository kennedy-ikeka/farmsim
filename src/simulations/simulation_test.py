from pydantic import ValidationError
import pytest
from pandas import DataFrame
from os.path import isdir, join

from models.asset import Asset
from src.models.cycle import Phase, Stock
from src.models.farm import FarmBusinessModel
from src.simulations.simulation import Simulation
from utils.config import DATA_DIR, TMP_DIR

class TestSimulation():
    @pytest.mark.parametrize("params", [
        {"id": "1"},
        {"id": "10"},
    ])
    def test_create_simulation(self, params):
        sim = Simulation(**params)
        assert sim.id == params["id"]
        assert sim.tag == f'Simulation_{params["id"]}'

    @pytest.mark.parametrize("params", [
        {"id": 2},
    ])
    def test_fail_create_invalid_simulation(self, params):
        with pytest.raises(ValidationError):
            Simulation(**params)

    @pytest.mark.parametrize("params", [
        {"domain": "random", "data": {"name": "Random"}}
    ])
    def test_add_metric(self, params):
        domain = params['domain']
        data = params['data']

        sim = Simulation()
        sim.add_metric(domain, '1', data)

        dataset = sim.datasets[domain]
        assert len(dataset) == 1

    @pytest.mark.parametrize("params", [
        {"assets": [{"kind": "Unknown", "id": "1"}], "id": "1", "kind": "Unknown"},
        {"assets": [{"kind": "Unknown", "id": "1"}, {"kind": "Random", "id": "1"}], "id": "1", "kind": "Unknown"}
    ])
    def test_get_asset(self, params):
        assets = params['assets']
        id = params['id']
        kind = params["kind"]

        sim = Simulation()
        [Asset(sim=sim, kind=a["kind"], id=a['id'])for a in assets]

        asset: Asset = sim.get_asset(kind, id)
        assert asset.id == id
        assert asset.kind == kind

    @pytest.mark.parametrize("params", [
        {"assets": [{"kind": "Unknown", "id": "1"}, {"kind": "Random", "id": "1"}], "kind": "Unknown", "ids": [], "count": 0},
        {"assets": [{"kind": "Unknown", "id": "1"}, {"kind": "Random", "id": "1"}], "kind": "Unknown", "ids": ["1"], "count": 1}
    ])
    def test_list_asset(self, params):
        assets = params['assets']
        ids = params['ids']
        kind = params["kind"]
        count = params["count"]

        sim = Simulation()
        [Asset(sim=sim, kind=a["kind"], id=a['id'])for a in assets]

        asset_list = sim.list_assets(kind, lambda a: a.id in ids)
        assert count == len(asset_list)

    @pytest.mark.parametrize("params", [
        {"business_models": [], "count": 0},
        {"business_models": [{"name": "Random", "capital": 1000000_00}], "count": 1},
        {"business_models": [{"name": "Random", "capital": 1000000_00}, {"name": "Another", "capital": 1000000_00}], "count": 2},
    ])
    def test_spawn_farm(self, params):
        business_models = params['business_models']
        count = params["count"]

        sim = Simulation()
        [sim.spawn_farm(b["name"], FarmBusinessModel(capital=b["capital"])) for b in business_models]

        farm_list = sim.list_assets("Farm")
        assert count == len(farm_list)
    
    @pytest.mark.parametrize("params", [
        {"duration": 10},
    ])
    def test_save(self, params):
        duration = params["duration"]

        phases = [
            Phase(duration, [1], 1, "Juveniles"), 
        ]
        stock = Stock(id=1, type="Catfish", phases=phases, size="Small_Fingerlin", count=10)
        farm_model = FarmBusinessModel(
            stocks=[stock],
            feed_conversion_rate={0: 1.1, 200: 1.3},
            feed_floating={0: True, 200: False},
        )

        sim = Simulation(business_models={"Random": farm_model}, out_dir=str(TMP_DIR))
        sim.run(duration)
        sim.save()

        sim_path = join(str(TMP_DIR), 'simulations', sim.timestamp.strftime("%d_%m_%Y_%H_%M_%S"))
        exists = isdir(sim_path)
        assert exists == True

