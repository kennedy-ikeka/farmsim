from datetime import datetime

import simpy

from models.simulation import SimulationModel
from src.models.feed import FeedBatch, FeedModel
from utils.conversion import to_kobo

class Feed(FeedModel):
    def __init__(self, sim: SimulationModel, name: str, size: float, floats=True, rate=1.0, verbose=0, active=True):
        super().__init__(sim, type="Feed", id=0, verbose=verbose, active=active)
        self.name = name
        self.size = size
        self.floats = floats
        self.rate = rate

        # The tag is a unique identifier for the feed stock, based on its name and size
        self.tag = f"{self.name}_{self.size}"

        # The different batches of the feed
        self.batches: list[FeedBatch] = []

        # Start the expiry process
        self.existence = self.env.process(self.exist())

    def __str__(self):
        return f"""
            size: {self.size}
            floats: {self.floats}
            rate: {self.rate}
            tag: {self.tag}
            batches: {len(self.batches)}
            quantity: {self.get_quantity()}
        """       

    def get_cost(self, weight: int):
        """Get the cost of weight of feed"""

        # Floatable feed are more expensive
        sink_rate = .8 if not self.floats else 1

        # Get the cost of a gram of the feed
        gram_rate = (self.rate/self.size) * sink_rate * 10

        # Get the cost
        return to_kobo(gram_rate * weight)

    def get_quantity(self):
        """Get the quantity of all feed batches"""
        return sum(b.stock.level for b in self.batches)   

    def consume(self, weight: float): 
        """Take out a specified weight from the feed stock"""

        counter = 0 # Initialize counter
        for b in self.batches: # Take starting from the earliest batch
            stock: simpy.Container = b.stock
            take = weight if stock.level >= weight else stock.level
            if take > 0:
                yield stock.get(take) # Update batch
                counter += take  # Update the counter and weight
                weight -= int(counter)      
                   
            if weight == 0: # Exit loop when the required weight is taken
                break

        # Remove the empty batches                
        self.batches = [b for b in self.batches if b.stock.level > 0]
        self.info(f"Took {counter} from stock")

    def refill(self, weight: float):
        """Add a new batch to the feed"""
        # Initialize batch
        batch = FeedBatch(self.env.now, simpy.Container(self.env, init=weight))

        # Add batch to feed
        self.batches.append(batch)

    def expire(self):
        """Expire feed batches"""       
        # Checks onces every day
        while self.active:
            yield self.env.timeout(1)
            self.info("Checking for expired feed batches")

            # Get the feed that are still okay
            now = self.env.now
            remaining = list(filter(lambda b: (now - b.time) <= 90, self.batches))

            # count expired feed and log it
            expired_count = len(self.batches) - len(remaining)
            self.info(f"Expired {expired_count} batches.")

            # remove the expired feed
            self.batches = remaining

    def exist(self):
        yield self.env.timeout(0)

        if self.active:
            # Start the expiry process
            self.expire_process = self.env.process(self.expire())