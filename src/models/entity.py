from typing import Callable, Optional

from faker import Generator
from pydantic import Field, computed_field
from simpy.core import SimTime
from simpy.events import Process
from simpy import Container

from src.utils.logger import Logger

class Entity(Logger):
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

    def terminate_after(self, delay: float):
        yield self.env.timeout(delay)
        yield self.env.process(self.terminate())
    