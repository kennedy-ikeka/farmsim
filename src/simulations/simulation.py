import os
from typing import Any, Callable, Mapping, Optional
from pydantic import Field
from pandas import DataFrame, concat, read_csv
import json

from models.asset import Asset
from src.models.farm import FarmBusinessModel
from src.models.simulation import SimulationModel
from src.simulations.farm import Farm


class Simulation(SimulationModel):
    business_models: dict[str, FarmBusinessModel] = Field(default_factory=dict, description="The business models of the farms")

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)
        for name, business_model in self.business_models.items():
            self.spawn_farm(name, business_model)

        self.processes["existence"] = self.env.process(self.exist())

    def exist(self):
        interval = self.options.get("checkpoint_interval", 1)
        while self.active:
            yield self.env.timeout(interval)
            self.info(f"Simulation at: {self.get_age()}")

            if self.store:
                self.save()

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

        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        csvs = filter(lambda x: x.endswith('.csv'), files)

        for f in csvs:
            file = f.split(".")[0]
            frame = read_csv(os.path.join(path, f))
            self.datasets[file] = frame.to_dict(orient="records")

        # with open(os.path.join(path, "settings.json"), "rb+") as s:
        #     settings = json.load(s)

        #     for key, value in settings["farms"].items():
        #         self.spawn_farm(key, FarmBusinessModel(**value))

    def save(self):
        """Save simulation data"""

        # set the id of the simulation
        id = self.timestamp.strftime("%d_%m_%Y_%H_%M_%S")

        # create the path
        path = os.path.join(self.out_dir, f'simulations/{id}')
        os.makedirs(path, exist_ok=True)

        # save each entities data collections as a single csv
        for table_name, table in self.datasets.items():
            frame = DataFrame(table).sort_values(by="time")
            frame.to_csv(f"{path}/{table_name}.csv", index=False)

        # farms = {name: fm.model_dump() for name, fm in self.farms.items()}
        # data = self.model_dump()

        # with open(f"{path}/settings.json", "w", encoding="utf-8") as f:
        #     json.dump(data, f, indent=2, ensure_ascii=False)
