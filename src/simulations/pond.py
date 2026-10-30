from typing import Optional

import numpy as np
from simpy import Container

from src.models.pond import POND_RENTAL_INTERVAL, PondModel

class Pond(PondModel):
    def model_post_init(self, __context):
        super().model_post_init(__context)

        self.containers["health"] = Container(env=self.env, capacity=100, init=self.options.get("health", 100))
        self.containers["water"] = Container(env=self.env, capacity=self.volume, init=self.volume)
        self.containers["feed"] = Container(env=self.env, init=0)
        self.processes["existence"] = self.env.process(self.exist())

    def get_cost(self, duration: Optional[int] = None) -> int:
        adjustment = 1.0
        if self.aerated:
            adjustment += 0.1 * self.density
        
        duration = duration if duration is not None else self.duration
        rent_rate = 1 if duration == 0 else duration * 0.1
        price = self.volume * self.details.cost * adjustment * rent_rate
        return int(price)

    def decontaminate(self):
        """Decontaminate the pond"""
    
        # Drain the water
        t_drain = self.drain_speed * self.containers['water'].level
        yield self.env.timeout(t_drain)

        if self.containers['water'].level > 0:
            yield self.containers['water'].get(self.containers['water'].level)
            self.info("Drained pond water")

        if self.containers['feed'].level > 0:
            yield self.containers['feed'].get(self.containers['feed'].level)

        # Fill the pond with clean water
        t_fill = self.drain_speed * self.volume
        yield self.env.timeout(t_fill)

        yield self.containers['water'].put(self.volume)
        self.info("Filled pond with clean water")

        yield self.containers['health'].put(self.containers['health'].capacity - self.containers['health'].level)
        self.info(f"Decontaminated pond, Health at {self.containers['health'].level}")

    def contaminate(self):
        """Contaminate the water in the pond"""
        while self.active:
            yield self.env.timeout(1)

            # Get the contermination rate based on the volumn of the pond
            base_rate = self.details.contamination_rate/self.volume

            # Get the effect of change in the pond health, min of 1 to avoid division by 0
            sick_effect = self.containers['health'].capacity / (max(1, self.containers['health'].level))

            # estimate the health lost
            health_lost = base_rate * sick_effect

            yield self.containers['health'].get(health_lost)
            self.info(f'Contaminated pond: Health at {self.containers['health'].level}')

    def spawn_feed(self):
        """Spawn feed in the pond"""
        while self.active:
            yield self.env.timeout(1)

            # Make sure there is water in the pond
            if self.containers['water'].level == 0:
                continue

            # Get the weight of feed to spawn based on the water level
            feed_weight = self.details.feed_spawn_rate * self.containers['water'].level

            yield self.containers['feed'].put(feed_weight)
            self.info(f"Spawned feed weighing {feed_weight:.2f} units")

    def seepage(self):
        ...
        # TODO

    def get_fish_by_id(self, fish_id: str):
        found = filter(lambda f: f.id == fish_id, self.fishes)
        return next(found) 

    def exist(self):
        yield self.env.timeout(0)
        
        if self.active:
            # Start the feed spawning process
            self.processes["spawn_feed"] = self.env.process(self.spawn_feed())
    
            # Start the contamination process
            self.processes["contaminate"] = self.env.process(self.contaminate())
