import simpy
import numpy as np

from src.models.feed import FeedModel

class Feed(FeedModel):
    def __init__(self, env, name: str, size: float, sinks=False, rate=1, verbose=True):
        super().__init__(env, name=f"Feed-{name}_{size}", verbose=verbose)
        self.env = env
        self.size = size
        self.sinks = sinks
        self.rate = rate

        # The tag is a unique identifier for the feed stock, based on its name and size
        self.tag = f"{self.name}_{self.size}"

        # The different batches of the feed
        self.batches = []
        self.expire_process = self.env.process(self.expire())

    def __str__(self):
        return f"""
            size: {self.size}
            sinks: {self.sinks}
            rate: {self.rate}
            tag: {self.tag}
            cost: {self.cost}
            batches: {len(self.batches)}
            quantity: {self.get_quantity()}
        """       

    def expire(self):
        """Expire feed batches"""       
        while True:
            yield self.env.timeout(1)
            self.log("Checking for expired feed batches")

            now = self.env.now
            remaining = list(filter(lambda b: (now - b['time']) <= 90, self.batches))
            expired_count = len(self.batches) - len(remaining)
            self.log(f"Expired {expired_count} batches.")
            
            self.batches = remaining

    def get_cost(self, weight):
        sink_rate = .7 if self.sinks else .8
        gram_rate = (self.rate/self.size) * sink_rate * 10
        # Get the cost in kilos
        return gram_rate * weight * 1000

    def get_quantity(self):
        return sum(b['stock'].level for b in self.batches)   

    def consume(self, weight): 
        taken = 0
        for b in self.batches:
            stock: simpy.Container = b['stock']
            t = weight if stock.level >= weight else stock.level
            yield stock.get(t)
            
            taken += t   
            weight -= taken         
            if weight == 0:
                break

        self.log(f"Took {taken} from stock")
        self.batches = [b for b in self.batches if b['stock'].level > 0]

    def refill(self, weight):
        batch = {
            'time': self.env.now, 
            'stock': simpy.Container(self.env, init=weight)
        }
        self.batches.append(batch)
