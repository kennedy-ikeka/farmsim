import os
from typing import Optional
from pydantic import Field
import numpy as np, pandas as pd
import json

from src.models.farm import FarmBusinessModel
from src.models.simulation import SimulationModel
from src.simulations.farm import Farm


class Simulation(SimulationModel):
    farms: dict[str, FarmBusinessModel] = Field(default_factory=dict, description="The business models of the farms")

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)


        for name, business_model in self.farms.items():
            self.spawn_farm(name, business_model)

        self.processes["checkpoint"] = self.env.process(self.checkpoint())

    def checkpoint(self):
        interval = self.options.get("checkpoint_interval", None)
        if interval is None:
            return
        
        while self.active:
            yield self.env.timeout(interval)
            self.save()
            self.info(f"Simulation at: {self.get_age()}")

    def run(self, until):
        """Run the simulation"""
        self.env.run(until=until) 

    def get_entity_frames(self, entity_name: str):
        # merge related entities as one
        asset_list = self.assets.get(entity_name, [])
        entity_frames: dict[str, pd.DataFrame] = {}

        for asset in asset_list:
            for table_name in asset.tables.keys():
                # get entities table data
                frame = asset.get_frame(table_name)
                if frame is None:
                    continue

                frames: pd.DataFrame = entity_frames.get(table_name, pd.DataFrame())
                entity_frames[table_name] = pd.concat([frames, frame])

        return entity_frames

    def set_entity_frames(self, entity_name: str, table_name: str, frames: pd.DataFrame):
        entity_list = self.assets.get(entity_name, [])
        for asset in entity_list:
            df = frames[frames['tag'] == asset.tag]
            asset.tables[table_name] = df.to_dict(orient="records")

    def load(self, path: str):
        exists = os.path.isdir(path)
        if not exists:
            raise ValueError(f"Simulation in path: {path} not found")

        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        csvs = filter(lambda x: x.endswith('.csv'), files)

        with open(os.path.join(path, "settings.json"), "rb+") as s:
            settings = json.load(s)

            for key, value in settings["farms"].items():
                self.spawn_farm(key, FarmBusinessModel(**value))

        for f in csvs:
            file = f.split(".")[0]
            entity_name, table_name = file.split("_")

            df = pd.read_csv(os.path.join(path, f))
            self.set_entity_frames(entity_name, table_name, df)

    def save(self):
        """Save simulation data"""

        # set the id of the simulation
        id = self.timestamp.strftime("%d_%m_%Y_%H_%M_%S")

        # create the path
        path = f'../data/simulations_{id}'
        os.makedirs(path, exist_ok=True)

        farms = {name: fm.model_dump() for name, fm in self.farms.items()}
        data = self.model_dump()

        with open(f"{path}/settings.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # save each entities data collections as a single csv
        for entity_name in self.assets.keys():
            entity_frames = self.get_entity_frames(entity_name)

            # merge as one dataframe
            for frame_name, frame in entity_frames.items():
                frame = frame.sort_values(by="time")
                frame.to_csv(f"{path}/{entity_name}_{frame_name}.csv", index=False)

    def spawn_farm(self, name: str, business_model = FarmBusinessModel()):
        self.info("Spawning Farm")
        id = len(self.farms.items())
        Farm(sim=self, id=str(id), name=name, business_model=business_model)
        self.farms[name] = business_model