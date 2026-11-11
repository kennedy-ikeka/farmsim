from typing import Callable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field
from simpy.core import SimTime, Environment
from simpy.events import Process
from simpy import Container

class Simlog(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    env: Environment = Field(default_factory=Environment, description="The simulation environment")
    kind: str = Field(..., description="The kind of entity")
    id: str = Field(default_factory=lambda: uuid4().hex, description="The id of the entity")
    verbose: int = Field(default=0, description="The log level", ge=0, le=3)

    @computed_field
    @property
    def tag(self) -> str:
        return f"{self.kind}_{self.id}"

    def error(self, message):
        if self.verbose >= 1:
            print(f"[Error] [{self.env.now}] {self.tag}: {message}")  

    def info(self, message: str):
        if self.verbose >= 2:
            print(f"[Info] [{self.env.now}] {self.tag}: {message}")    


class Entity(Simlog):
    active: bool = Field(default=True, description="The active status of the entity")
    processes: dict[str, Process] = Field(default_factory=dict, description="The entity processes")
    containers: dict[str, Container] = Field(default_factory=dict, description="The entity containers")
    schedules: dict[str, float] = Field(default_factory=dict, description="Schedules for processes")
    options: dict = Field(default_factory=dict, description="Optional parameters")
    start_time: SimTime = Field(default=0, description="The time entity was initialized")
    stop_time: SimTime = Field(default=0, description="The time entity was terminated")
        
    def model_post_init(self, __context):
        super().model_post_init(__context)

    def run(self, until):
        """Run the entity"""
        if not self.active:
            return
        self.env.run(until=until)   

    def get_age(self):
        return int(self.env.now - self.start_time)

    def terminate(self):
        yield self.env.timeout(0)
        self.active = False

    def schedule(self, delay: float, fn: Callable, kwargs: dict = {}):
        yield self.env.timeout(delay)
        yield self.env.process(fn(**kwargs))
    