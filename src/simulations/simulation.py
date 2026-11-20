import os
from typing import Callable, Optional
from pydantic import Field
from pandas import DataFrame, read_csv
import json

from models.asset import Asset
from simulations.batch import Batch
from simulations.cycle import Cycle
from simulations.feed import Feed
from simulations.fish import Fish
from simulations.pond import Pond
from src.models.farm import FarmBusinessModel
from src.models.simulation import SimulationModel
from src.simulations.farm import Farm
from utils.conversion import DAYS_IN_MONTHS, HOURS_IN_DAY, MONTHS_IN_YEAR

ASSET_TYPES: dict[str, type[Asset]] = {
    cls.__name__: cls 
    for cls in (Farm, Cycle, Batch, Fish, Pond, Feed)
}

class Simulation(SimulationModel):
    business_models: dict[str, FarmBusinessModel] = Field(default_factory=dict, description="The business models of the farms")

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)
        for name, business_model in self.business_models.items():
            self.spawn_farm(name, business_model)

        self.processes["existence"] = self.env.process(self.exist())

    def exist(self):
        while self.active:
            yield self.env.timeout(self.checkpoint_interval)
            self.info(f"Simulation at: {self.get_age()}")

    def get_asset[T: Asset](self, asset_type: str, id: str) -> T:
        asset_collection = self.assets.get(asset_type, {})
        asset = asset_collection.get(id, None)
        if asset is None:
            raise ValueError("Asset not found")
        return asset
    
    def list_assets[T: Asset](self, asset_type: str, where: Optional[Callable[[T], bool]]=None) -> list[T]:
        collection = self.assets.get(asset_type, {})
        if not where:
            return list(collection.values())
        
        return [
            asset
            for asset in collection.values()
            if where(asset)
        ]

    def add_metric(self, domain: str, asset_id: str, data: dict):
        table = self.datasets.get(domain, None)
        if not table:
            self.datasets[domain] = []
            table = self.datasets[domain]

        table.append({"time": self.env.now, "id": asset_id, **data})
        self.info(f"{domain}: {data}")

    def spawn_farm(self, name: str, business_model = FarmBusinessModel()):
        self.info("Spawning Farm")
        id = len(self.business_models.items())
        Farm(sim=self, id=str(id), name=name, business_model=business_model)
        self.business_models[name] = business_model

    def load(self, path: str):
        exists = os.path.isdir(path)
        if not exists:
            raise ValueError(f"Simulation in path: {path} not found")

        # Load datasets
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        csvs = filter(lambda x: x.endswith('.csv'), files)

        for f in csvs:
            file = f.split(".")[0]
            frame = read_csv(os.path.join(path, f))
            self.datasets[file] = frame.to_dict(orient="records")

        # Load settings
        with open(f'{path}/settings.json', "rb+") as s:
            settings = json.load(s)

            # Load config
            for k, v in settings['config'].items():
                setattr(self, k, v)

            # Load assets
            for k, v in settings['assets'].items():
                for i, a in v.items():
                    ASSET_TYPES[k](**a, sim=self)

    def save(self):
        """Save simulation data"""

        # set the id of the simulation
        # create the path
        path = os.path.join(self.out_dir, f'simulations/{self.timestamp}')
        os.makedirs(path, exist_ok=True)

        # save each entities data collections as a single csv
        for table_name, table in self.datasets.items():
            frame = DataFrame(table).sort_values(by="time")
            frame.to_csv(f"{path}/{table_name}.csv", index=False)

        assets = {
            t: {
                i: a.get_state()
                for i, a in d.items()
            }
            for t, d in self.assets.items()
        }
                
        config = self.get_state(exclude={'assets', 'datasets'})
        settings = {
            "config": config,
            "assets": assets
        }

        with open(f'{path}/settings.json', "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    def inflated_price(self, price: float):
        months = self.get_age() // DAYS_IN_MONTHS
        years = months / MONTHS_IN_YEAR
        return (1 + self.inflation_rate * years) * price