import simpy
import numpy as np

from src.simulations.entity import Entity

class Feed(Entity):
    def __init__(self, env, name: str, size: int, sinks=False, rate=1):
        super().__init__(env, name=f"Feed-{name}")
        self.size = size
        self.sinks = sinks
        self.rate = rate

    def expire_process(self):
        ...        

class FeedStock(Feed):
    def __init__(self, env, name: str, size: int, quantity: int, sinks=False, rate=1):
        super().__init__(env, name=f"Feed-{name}", size=size, sinks=sinks, rate=rate)

        # The cost per kilo is based on the size, rate and the sink ability of the feed
        self.cost = (10000 * self.rate * (1/self.size)) + (100 if not self.sinks else 0)

        # The stock is a simpy container that holds the quantity of feed available
        self.stock = simpy.Container(env=env, init=quantity)

        # The tag is a unique identifier for the feed stock, based on its name and size
        self.tag = f"{self.name}_{self.size}"

    def take(self, quantity):
        yield self.stock.get(quantity)

    def refill(self, quantity):
        yield self.stock.put(quantity)
