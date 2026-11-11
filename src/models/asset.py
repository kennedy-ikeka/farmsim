from pydantic import Field, computed_field
import numpy as np
import pandas as pd

from src.models.entity import Entity
from src.models.simulation import SimulationModel

class Asset(Entity):
    sim: SimulationModel = Field(default_factory=lambda: SimulationModel(), description="The simulation object")

    @computed_field
    @property
    def rng(self) -> np.random.Generator:
        return self._rng

    def model_post_init(self, __context):
        super().model_post_init(__context)
        self._rng = np.random.default_rng(self.sim.seed)
        self.env = self.sim.env
        self.plug_in()

    def plug_in(self):
        type_entities: dict = self.sim.assets.get(self.kind, {})
        type_entities[self.id]  = self
        self.sim.assets[self.kind] = type_entities 

    def plug_out(self):
        ...

    def get_state(self, exclude: set):
        return self.model_dump(
            exclude_computed_fields=True,
            exclude={"sim", "env", "processes", "conatainers", "schedules", *exclude}
        )
