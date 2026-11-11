from datetime import datetime
from typing import Callable, Generator, Optional

from pandas import DataFrame
from pydantic import Field

from src.models.entity import Entity
from utils.config import DATA_DIR

class SimulationModel(Entity):
    assets: dict[str, dict] = Field(default_factory=dict, description="The simulation assets")
    timestamp: datetime = Field(default=datetime.now(), description="The time the simulation started")
    seed: int = Field(default=0, description="The simulation seed")
    store: bool = Field(default=False, description="Save the simulation")
    kind: str = Field(default="Simulation")
    datasets: dict[str, list[dict]] = Field(default_factory=dict, description="The tables for the entity")
    out_dir: str = Field(default=DATA_DIR, description="The directory to store dataset")

    def load(self, path: str):
        ...

    def save(self, path: str):
        ...

    def get_frames(self, entity_name: str) -> dict[str, DataFrame]:
        ...

    def set_frames(self, entity_name: str, table_name: str, frames: DataFrame):
        ...

    def spawn_farm(self):
        ...

    def exist(self) -> Generator:
        ...

    def metric(self, domain: str, id: str, data: dict):
        ...

    def get_asset[T](self, asset_type: str, id: str) -> T:
        ...

    def list_assets[T](self, asset_type: str, where: Optional[Callable[[T], bool]]) -> list[T]:
        ...
