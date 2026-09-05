import simpy
import numpy as np

from src.simulations.entity import Entity

class Pond(Entity):
    def __init__(self, env, tag, height, width, depth, contaminate_rate=0.001, feed_spawn_rate=0.001, verbose=True):
        super().__init__(env, name=f"Pond-{tag}", verbose=verbose)
        self.tag = tag
        self.height = height
        self.width = width
        self.depth = depth
        self.volumn = height * width * depth
        
        self.health = simpy.Container(env=env, capacity=100, init=100)
        self.water = simpy.Container(env=env, capacity=self.volumn, init=self.volumn)
        self.feed = simpy.Container(env=env, init=0)
        self.contaminate_rate = contaminate_rate
        self.feed_spawn_rate = feed_spawn_rate

        self.fishes = []

        # Start the contamination process
        self.env.process(self.contaminate())

        # Start the feed spawning process
        self.env.process(self.spawn_feed())

    def get_feed_capacity(self):
        return self.volumn * 0.1

    def spawn_feed(self):
        """Spawn feed in the pond"""
        while True:
            t_spawn = np.random.exponential(1/4)
            yield self.env.timeout(t_spawn)

            feed_capacity = self.get_feed_capacity()
            feed_weight = self.feed_spawn_rate * feed_capacity
            yield self.feed.put(feed_weight)
            self.log(f"Spawned feed weighing {feed_weight:.2f} units")

    def decontaminate(self):
        """Decontaminate the pond"""

        # Drain the water
        t_drain = np.random.exponential(1/24)
        yield self.env.timeout(t_drain)
        yield self.water.get(self.water.level)
        self.log("Drained pond water")

        # Fill the pond with clean water    
        t_fill = np.random.exponential(1/24)
        yield self.env.timeout(t_fill)
        yield self.water.put(self.volumn)
        yield self.health.put(self.health.capacity - self.health.level)
        self.log("Decontaminated pond")

    def contaminate(self):
        """Contaminate the water in the pond"""
        while True:
            t_contaminate = np.random.exponential(1/6)
            yield self.env.timeout(t_contaminate)

            yield self.health.get(self.contaminate_rate)
            self.log('Contaminated pond')

    def run(self, until=100):
        """Run the pond simulation"""
        self.env.run(until=until)