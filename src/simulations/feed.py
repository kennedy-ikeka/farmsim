import simpy

from src.models.entity import Entity
from src.models.feed import FeedModel

class Feed(FeedModel, Entity):
    def __init__(self, env, name: str, size: float, sinks=False, rate=1, verbose=False):
        super().__init__(env, tag=f"Feed-{name}_{size}", verbose=verbose)
        self.env = env
        self.name = name
        self.size = size
        self.sinks = sinks
        self.rate = rate

        # The tag is a unique identifier for the feed stock, based on its name and size
        self.tag = f"{self.name}_{self.size}"

        # The different batches of the feed
        self.batches = []

        # Start the expiry process
        self.expire_process = self.env.process(self.expire())

    def __str__(self):
        return f"""
            size: {self.size}
            sinks: {self.sinks}
            rate: {self.rate}
            tag: {self.tag}
            batches: {len(self.batches)}
            quantity: {self.get_quantity()}
        """       

    def get_cost(self, weight: float):
        """Get the cost of weight of feed"""

        # Floatable feed are more expensive
        sink_rate = .8 if self.sinks else 1

        # Get the cost of a gram of the feed
        gram_rate = (self.rate/self.size) * sink_rate * 10

        # Get the cost in kilos
        return gram_rate * weight * 1000

    def get_quantity(self):
        """Get the quantity of all feed batches"""
        return sum(b['stock'].level for b in self.batches)   

    def consume(self, weight: float): 
        """Take out a specified weight from the feed stock"""

        counter = 0 # Initialize counter
        for b in self.batches: # Take starting from the earliest batch
            stock: simpy.Container = b['stock']
            take = weight if stock.level >= weight else stock.level
            yield stock.get(take) # Update batch
            
            counter += take  # Update the counter and weight
            weight -= counter         
            if weight == 0: # Exit loop when the required weight is taken
                break

        # Remove the empty batches                
        self.batches = [b for b in self.batches if b['stock'].level > 0]
        self.log(f"Took {counter} from stock")

    def refill(self, weight: float):
        """Add a new batch to the feed"""
        # Initialize batch
        batch = {
            'time': self.env.now, 
            'stock': simpy.Container(self.env, init=weight)
        }
        # Add batch to feed
        self.batches.append(batch)

    def expire(self):
        """Expire feed batches"""       
        while True:
            # Checks onces every day
            yield self.env.timeout(1)
            self.log("Checking for expired feed batches")

            # Get the feed that are still okay
            now = self.env.now
            remaining = list(filter(lambda b: (now - b['time']) <= 90, self.batches))

            # count expired feed and log it
            expired_count = len(self.batches) - len(remaining)
            self.log(f"Expired {expired_count} batches.")

            # remove the expired feed
            self.batches = remaining