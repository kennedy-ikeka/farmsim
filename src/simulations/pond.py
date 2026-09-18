from math import sqrt

import simpy
import numpy as np

from src.models.pond import POND_BASE_COSTS, POND_CONTAMINATION_RATE, POND_SPAWN_FEED_RATE, POND_TYPES, PondModel


class Pond(PondModel):
    def __init__(self, env, id: int, type: POND_TYPES, length=1.0, width=1.0, depth=1.0, density = 1.0, rental_rate=0.1, aerated=False, verbose=False):
        super().__init__(env, f"{type}_{id}", verbose=verbose)
        self.id = id
        self.length = length
        self.width = width
        self.depth = depth
        self.volume = length * width * depth
        self.type = type
        self.density = density
        self.capacity = self.volume * density
        self.aerated = aerated
        self.rental_rate = rental_rate
        
        self.health = simpy.Container(env=env, capacity=100, init=100)
        self.water = simpy.Container(env=env, capacity=self.volume, init=self.volume)
        self.feed = simpy.Container(env=env, init=0)
        self.fishes = []

        # Start the contamination process
        self.contaminate_process = self.env.process(self.contaminate())

        # Start the feed spawning process
        self.spawn_feed_process = self.env.process(self.spawn_feed())

    def get_feed_availability(self) -> float:
        feed = self.feed.level
        size = sqrt(self.length * self.width)
        return feed / size

    def get_cost(self):
        base_cost = POND_BASE_COSTS[self.type]
        adjustment = 1.0
        if self.aerated:
            adjustment += 0.1 * self.density
        return self.volume * base_cost * adjustment 

    def get_rent_cost(self, duration=1):
        cost = self.get_cost()
        return cost * self.rental_rate * duration

    def spawn_feed(self):
        """Spawn feed in the pond"""
        while True:
            t_spawn = self.rng.exponential(1/4)
            yield self.env.timeout(t_spawn)

            feed_capacity = self.volume * 0.1
            spawn_rate = POND_SPAWN_FEED_RATE[self.type]
            feed_weight = spawn_rate * feed_capacity
            yield self.feed.put(feed_weight)
            self.log(f"Spawned feed weighing {feed_weight:.2f} units")

    def decontaminate(self):
        """Decontaminate the pond"""
    
        # Drain the water
        t_drain = self.rng.exponential(1/24)
        yield self.env.timeout(t_drain)
        yield self.water.get(self.water.level)
        self.log("Drained pond water")

        # Fill the pond with clean water    
        t_fill = self.rng.exponential(1/24)
        yield self.env.timeout(t_fill)
        yield self.water.put(self.volume)
        yield self.health.put(self.health.capacity - self.health.level)
        self.log("Decontaminated pond")

    def contaminate(self):
        """Contaminate the water in the pond"""
        while True:
            t_contaminate = self.rng.exponential(1/6)
            yield self.env.timeout(t_contaminate)

            base_rate = POND_CONTAMINATION_RATE[self.type]/self.volume
            sick_effect = (self.health.capacity / (max(1, self.health.level)))
            contaminate_rate = base_rate * sick_effect
            yield self.health.get(contaminate_rate)
            self.log('Contaminated pond')

    def get_fish_by_id(self, id):
        found = filter(lambda f: f.id == id, self.fishes)
        return next(found) 
