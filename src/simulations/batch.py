import numpy as np
from faker import Faker
from pydantic import Field, computed_field

from src.models.fish import FISH_SIZE_DETAILS
from src.models.batch import BatchModel
from src.models.farm import FarmModel
from src.simulations.feed import Feed
from src.utils.conversion import to_kilo, to_gram
from src.utils.helper import get_param

faker = Faker()

class Batch(BatchModel):
    farm_id: str = Field(..., description="The farm id for the batch")

    @computed_field
    @property
    def farm(self) -> FarmModel:
        return self.sim.get_asset("Farm", self.farm_id)

    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)
        
        self.schedules["next_feeding"] = 1
        self.pond.fish_ids = self.fish_ids
        
        for fish_id in self.fish_ids:
            f = self.sim.get_asset("Fish", fish_id)
            f.batch_id = self.id
            f.pond_id = self.pond_id

        self.processes["existence"] = self.env.process(self.exist())

    def get_batch_weight(self):
        return np.median([f.containers['weight'].level for f in self.pond.get_fishes()]) if self.pond.fish_ids else 0

    def get_next_feeding_time(self):
        """Get the next time to feed the fishes based on feeding hours"""
        
        feeding_hours: list = get_param(self.farm.business_model.feeding_hours, self.get_batch_weight())            

        # Get the current hour of the day
        now = self.env.now
        day = int(now)
        current_hour = round((now - day) * 24, 4)

        # Check the next feeding hour
        for hour in feeding_hours:
            if hour > current_hour:
                return round(day + (hour/24) - now, 6)

        # If all feeding hours have passed, return the first feeding hour of the next day
        return round(day + 1 + (feeding_hours[0]/24) - now, 6)

    def get_feed_size(self):
        """Get the appropriate feed size based on the median weight of the fishes"""
        all_sizes = list(FISH_SIZE_DETAILS.values())
        feed_size = all_sizes[-1].feed_size

        for fish_size in all_sizes:
            if fish_size.min_size <= self.get_batch_weight() < fish_size.max_size:
                return fish_size.feed_size

        return feed_size

    def get_feed(self):
        """Get the appropriate feed in stock based on the median weight of the fishes"""
        size = self.get_feed_size()
        feeds = self.sim.list_assets("Feed", lambda c: getattr(c, 'id') in self.farm.feed_ids)
        for f in feeds:
            if f.size == size:
                return f

    def feed_fishes(self):
        """Feed the fishes in the pond"""
        while self.active:
            self.info(f"Next feeding in {self.schedules["next_feeding"] * 24} hours")
            yield self.env.timeout(self.schedules["next_feeding"])

            # Get the feed to be consumed by each fish
            total_feed = sum([f.get_hunger_weight() for f in self.pond.get_fishes()])
            if total_feed == 0:
                continue

            # select the appropriate feed
            feed = self.get_feed()
            if feed == None:
                # buy feed
                self.info(f'Appropriate feed not found')
                feed_size = self.get_feed_size()

                weight = self.get_batch_weight()
                rate: float = get_param(self.farm.business_model.feed_conversion_rate, weight)
                floats: bool = get_param(self.farm.business_model.feed_floating, weight)  
                id = len(self.farm.feed_ids)
                feed = Feed(
                    sim=self.sim, 
                    name=faker.name(), 
                    farm_id=self.farm_id,
                    size=feed_size, 
                    rate=rate, 
                    floats=floats,
                    id=str(id)
                )            

            # Should refill feed?
            remaining_feed = feed.get_quantity()
            purchase_feed = to_gram(np.max([to_kilo(total_feed), 1])) # buy atleast 1 kilo of feed

            if remaining_feed < total_feed:
                self.info(f'Feed not enough to for fishes')
                yield self.sim.env.process(self.farm.stock_feed(feed=feed, weight=purchase_feed))


            # Update the feed stock
            self.info(f'Taking feed of weight: {total_feed}')
            yield self.sim.env.process(feed.consume(total_feed))

            # Feed fishes and update their hunger
            self.info(f'Pour feed into pond')
            yield self.pond.containers['feed'].put(total_feed)

            # Update the next feed time
            self.schedules["next_feeding"] = self.get_next_feeding_time()

            # Log feeding data
            self.sim.add_metric("fish-feeding", self.farm_id, {
                'time': self.env.now,
                'feed': feed.tag,
                'total_feed': total_feed,
                'fcr': feed.rate,
                'size': feed.size,
                'batch_id': self.id,
                'cycle_id': self.cycle_id
            })

    def maintain_pond(self):
        """Keep the pond healthy and secure for the fishes"""
        while self.active:
            contamination_rate = 1 - (self.pond.containers['health'].level/self.pond.containers['health'].capacity)
            pond_contamination_limit: float = get_param(self.farm.business_model.pond_contamination_limit, self.get_batch_weight()) 
            dirty = contamination_rate >= pond_contamination_limit
            if dirty:
                self.info(f'Pond health is low, decontaminating')
                yield self.env.process(self.pond.decontaminate())
            yield self.env.timeout(1)

    def expire(self):
        while self.active:
            yield self.env.timeout(1)
            age = self.get_age()
            if age >= self.duration:
                yield self.env.process(self.terminate())

    def exist(self):
        if self.active:
            self.env.process(self.schedule(self.duration, self.terminate))
            
            self.processes['fish_feeding'] = self.env.process(self.feed_fishes())
            self.processes['pond_maintainance'] = self.env.process(self.maintain_pond())
            self.processes['expiry'] = self.env.process(self.expire())

        yield self.env.timeout(0)
                
    def terminate(self):
        self.pond.fish_ids = []
        self.active = False
        yield self.env.timeout(0)


        
