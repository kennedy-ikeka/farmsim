from datetime import datetime
from typing import Callable, Generator, Optional

from pydantic import Field

from src.models.entity import Entity
from utils.config import DATA_DIR

class SimulationModel(Entity):
    assets: dict[str, dict] = Field(default_factory=dict, description="The simulation assets")
    timestamp: str = Field(default=datetime.now().strftime("%Y_%m_%d_%H_%M_%S"), description="The time the simulation started")
    seed: int = Field(default=0, description="The simulation seed")
    store: bool = Field(default=False, description="Save the simulation")
    kind: str = Field(default="Simulation")
    datasets: dict[str, list[dict]] = Field(default_factory=dict, description="The tables for the entity")
    out_dir: str = Field(default=DATA_DIR, description="The directory to store dataset")
    checkpoint_interval: int = Field(default=1, description="Optional parameters")

    def load(self, path: str):
        ...

    def save(self, path: str):
        ...

    def spawn_farm(self):
        ...

    def exist(self) -> Generator:
        ...

    def add_metric(self, domain: str, id: str, data: dict):
        ...

    def get_asset[T](self, asset_type: str, id: str) -> T:
        ...

    def list_assets[T](self, asset_type: str, where: Optional[Callable[[T], bool]]) -> list[T]:
        ...
