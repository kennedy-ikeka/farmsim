from typing import Any, Optional

import numpy as np
from faker import Faker

from models.animal import FISH_SIZE_DETAILS, FishModel
from models.batch import BatchModel
from models.farm import FarmModel
from models.pond import PondModel
from simulations.feed import Feed
from utils.conversion import to_kilo
from utils.helper import get_param

faker = Faker()

class Batch(BatchModel):
    feeding = 0
    def __init__(self, id: int, farm: FarmModel, pond: PondModel, fishes: list[FishModel], cycle_id: int, duration: int, verbose=0, active=True, seed=0) -> None:
        super().__init__(pond.env, type="Batch", id=id, verbose=verbose, active=active, seed=seed)
        self.farm = farm

        if len(fishes) == 0:
            raise ValueError("There must be atleast 1 fish in a batch")
        
        self.fishes = fishes
        self.count = len(self.fishes)
        self.duration = duration
        self.cycle_id = cycle_id
        self.pond = pond
        self.start_time = self.env.now
        self.t_next_feeding = 1

        self.existence = self.env.process(self.exist())


    def get_next_feeding_time(self):
        """Get the next time to feed the fishes based on feeding hours"""
        weight = np.median([f.weight.level for f in self.fishes])
        feeding_hours: list = get_param(self.farm.farming_model.feeding_hours, weight)            

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
        median_weight = np.median([f.weight.level for f in self.fishes])
        all_sizes = list(FISH_SIZE_DETAILS.values())
        feed_size = all_sizes[-1].feed_size

        for fish_size in all_sizes:
            if fish_size.min_size <= median_weight < fish_size.max_size:
                return fish_size.feed_size

        return feed_size

    def get_feed(self):
        """Get the appropriate feed in stock based on the median weight of the fishes"""
        size = self.get_feed_size()
        for f in self.farm.feeds:
            if f.size == size:
                return f

    def feed_fishes(self):
        """Feed the fishes in the pond"""
        while self.active:
            self.info(f"Next feeding in {self.t_next_feeding * 24} hours")
            yield self.env.timeout(self.t_next_feeding)

            # Get the feed to be consumed by each fish
            total_feed = sum([f.get_hunger_weight() for f in self.fishes])
            if total_feed == 0:
                continue

            # select the appropriate feed
            feed = self.get_feed()
            if feed == None:
                # buy feed
                self.info(f'Appropriate feed not found')
                feed_size = self.get_feed_size()

                weight = np.median([f.weight.level for f in self.fishes])
                rate: float = get_param(self.farm.farming_model.feed_conversion_rate, weight)  
                feed = Feed(env=self.env, name=faker.name(), size=feed_size, seed=self.seed, rate=rate)            

            # Should refill feed?
            remaining_feed = feed.get_quantity()
            total_feed_kilos = to_kilo(total_feed)
            if remaining_feed < total_feed_kilos:
                self.info(f'Feed not enough to for fishes')
                yield self.env.process(self.farm.stock_feed(feed=feed, weight=total_feed_kilos))

            # Update the feed stock
            self.info(f'Taking feed of weight: {total_feed_kilos}')
            yield self.env.process(feed.consume(total_feed_kilos))
                
            # Feed fishes and update their hunger
            self.info(f'Pour feed into pond')
            yield self.pond.feed.put(total_feed)

            # Update the next feed time
            self.t_next_feeding = self.get_next_feeding_time()

            # Log feeding data
            self.farm.metric("feeding", {
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
            yield self.env.timeout(1)

            contamination_rate = 1 - (self.pond.health.level/self.pond.health.capacity)
            weight = np.median([f.weight.level for f in self.fishes])
            pond_contamination_limit: float = get_param(self.farm.farming_model.pond_contamination_limit, weight) 
            dirty = contamination_rate >= pond_contamination_limit
            if dirty:
                self.info(f'Pond health is low, decontaminating')
                yield self.env.process(self.pond.decontaminate())

    def expire(self):
        while self.active:
            yield self.env.timeout(1)
            age = self.get_age()
            if age >= self.duration:
                yield self.env.process(self.terminate())

    def exist(self):
        yield self.env.timeout(0)

        self.pond.fishes = self.fishes
        for f in self.fishes:
            f.batch_id = self.id
            f.set_pond(pond=self.pond)

        if self.active:
            self.feeding_process = self.env.process(self.feed_fishes())
            self.pond_process = self.env.process(self.maintain_pond())
            self.expire_process = self.env.process(self.expire())
                
    def terminate(self):
        self.active = False
        self.pond.fishes = []
        yield self.env.timeout(0)
