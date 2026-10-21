from datetime import datetime

import simpy
import numpy as np

from models.simulation import SimulationModel
from src.models.pond import POND_RENTAL_INTERVAL, POND_TYPE_DETAILS, POND_TYPES, PondModel
from utils.conversion import DAY_IN_HOURS, HOUR_IN_MINUTES

class Pond(PondModel):
    def __init__(self, sim: SimulationModel, id: int, type: POND_TYPES, length=1.0, width=1.0, depth=1.0, density = 1.0, health=100, duration: int=0, aerated=False, verbose=0, active=True):
        super().__init__(sim, type=type, id=id, verbose=verbose, active=active)
        self.id = id
        self.length = length
        self.width = width
        self.depth = depth
        self.volume = length * width * depth
        self.type = type
        self.density = density
        self.capacity = self.volume * density
        self.aerated = aerated
        self.since = self.env.now
        
        self.health = simpy.Container(env=self.env, capacity=100, init=health)
        self.water = simpy.Container(env=self.env, capacity=self.volume, init=self.volume)
        self.feed = simpy.Container(env=self.env, init=0)
        self.fishes = []

        # ponds are rented in POND_RENTAL_INTERVALs
        self.duration = np.ceil(duration/POND_RENTAL_INTERVAL) * POND_RENTAL_INTERVAL
        self.pond_details = POND_TYPE_DETAILS[self.type]

        self.existence = self.env.process(self.exist())
        self.drain_speed = np.random.randint(30, 40) / HOUR_IN_MINUTES / DAY_IN_HOURS  # drain speed in days

    def get_cost(self, duration=0) -> int:
        base_cost = self.pond_details.cost
        adjustment = 1.0
        if self.aerated:
            adjustment += 0.1 * self.density
        
        duration = self.duration if duration == 0 else duration
        rent_rate = 1 if duration == 0 else (self.duration/365) * 0.1
        price = self.volume * base_cost * adjustment * rent_rate
        return int(price)

    def decontaminate(self):
        """Decontaminate the pond"""
    
        # Drain the water
        t_drain = self.drain_speed * self.water.level
        yield self.env.timeout(t_drain)

        if self.water.level == 0:
            return

        yield self.water.get(self.water.level)
        self.info("Drained pond water")

        yield self.feed.get(self.feed.level)

        # Fill the pond with clean water
        t_fill = self.drain_speed * self.volume
        yield self.env.timeout(t_fill)

        yield self.water.put(self.volume)
        self.info("Filled pond with clean water")

        yield self.health.put(self.health.capacity - self.health.level)
        self.info(f"Decontaminated pond, Health at {self.health.level}")

    def contaminate(self):
        """Contaminate the water in the pond"""
        while self.active:
            yield self.env.timeout(1)

            # Get the contermination rate based on the volumn of the pond
            base_rate = self.pond_details.contamination_rate/self.volume

            # Get the effect of change in the pond health, min of 1 to avoid division by 0
            sick_effect = self.health.capacity / (max(1, self.health.level))

            # estimate the health lost
            health_lost = base_rate * sick_effect

            yield self.health.get(health_lost)
            self.info(f'Contaminated pond: Health at {self.health.level}')

    def spawn_feed(self):
        """Spawn feed in the pond"""
        while self.active:
            yield self.env.timeout(1)

            # Make sure there is water in the pond
            if self.water.level == 0:
                continue

            # Get the weight of feed to spawn based on the water level
            feed_weight = self.pond_details.feed_spawn_rate * self.water.level

            yield self.feed.put(feed_weight)
            self.info(f"Spawned feed weighing {feed_weight:.2f} units")

    def seepage(self):
        ...
        # TODO

    def get_fish_by_id(self, fish_id: int):
        found = filter(lambda f: f.id == fish_id, self.fishes)
        return next(found) 

    def exist(self):
        yield self.env.timeout(0)
        
        if self.active:
            # Start the feed spawning process
            self.spawn_feed_process = self.env.process(self.spawn_feed())
    
            # Start the contamination process
            self.contaminate_process = self.env.process(self.contaminate())
