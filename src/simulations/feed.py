from simpy import Container

from src.models.feed import FeedModel
from src.utils.conversion import to_kobo

class Feed(FeedModel):
    def model_post_init(self, __context):
        super().model_post_init(__context)
        
        # Start the expiry process
        self.processes['existence'] = self.env.process(self.exist())    

    def get_cost(self, weight: int):
        """Get the cost of weight of feed"""

        # Floatable feed are more expensive
        sink_rate = .8 if not self.floats else 1

        # Get the cost of a gram of the feed
        gram_rate = (self.rate/self.size) * sink_rate * 10

        # Get the cost

        cost = self.sim.inflated_price(gram_rate * weight)
        return to_kobo(cost)

    def get_quantity(self):
        """Get the quantity of all feed batches"""
        return sum(b.level for b in self.containers.values())   

    def consume(self, weight: float): 
        """Take out a specified weight from the feed stock"""

        counter = 0 # Initialize counter
        for t, b in self.containers.items(): # Take starting from the earliest batch
            take = weight if b.level >= weight else b.level
            if take > 0:
                yield b.get(take) # Update batch
                counter += take  # Update the counter and weight
                weight -= int(counter)      
                   
            if weight == 0: # Exit loop when the required weight is taken
                break

        # Remove the empty batches                
        self.containers = {k: b for k, b in self.containers.items() if b.level > 0}
        self.info(f"Took {counter} from stock")

    def refill(self, weight: float):
        """Add a new batch to the feed"""
        i = len(self.containers)
        self.containers[f'{self.env.now}_{i}'] = Container(self.env, init=weight)

    def expire(self, issolated=False):
        """Expire feed batches"""       
        # Checks onces every day
        while self.active or issolated:
            yield self.env.timeout(1)
            self.info("Checking for expired feed batches")

            # Get the feed that are still okay
            now = self.env.now
            remaining = {
                k: b 
                for k, b in self.containers.items() 
                if (now - float(k.split('_')[0])) <= 90
            }
            
            # count expired feed and log it
            expired_count = len(self.containers.keys()) - len(remaining.keys())
            self.info(f"Expired {expired_count} batches.")

            # remove the expired feed
            self.containers = remaining

    def exist(self):
        yield self.env.timeout(0)

        if self.active:
            # Start the expiry process
            self.processes['expire'] = self.env.process(self.expire())