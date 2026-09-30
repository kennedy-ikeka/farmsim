from typing import Optional

import numpy as np
from faker import Faker

from models.animal import FISH_SIZE_DETAILS, FishModel
from models.batch import BatchModel
from models.farm import FarmModel
from models.pond import PondModel
from simulations.feed import Feed

faker = Faker()

class Batch(BatchModel):
    def __init__(self, farm: FarmModel, pond: PondModel, fishes: list[FishModel], stock_id: str, duration: int, count: int) -> None:
        self.id = f"{pond.tag}_{stock_id}"

        super().__init__(pond.env, tag=f"Batch_{self.id}")
        self.farm = farm
        self.fishes = fishes
        self.count = count
        self.duration = duration
        self.stock_id = stock_id
        self.pond = pond
        self.start_time = self.env.now
        self.active = True

        self.existence = self.env.process(self.exist())

    def get_age(self):
        return int(self.env.now - self.start_time)

    def exist(self):
        self.pond.fishes = self.fishes
        for f in self.fishes:
            f.set_pond(pond=self.pond)

        while self.active:
            yield self.env.process(self.feed_fishes())
            yield self.env.process(self.clean_pond())

            age = self.get_age()
            self.active = age <= self.duration

    def get_feeding_hours(self):
        """Get the feeding timetable"""
        return [9, 17] # 9am, 5pm

    def get_next_feeding_time(self):
        """Get the next time to feed the fishes based on feeding hours"""
        feeding_hours = self.get_feeding_hours() # Get the feeding hours

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
        all_size = list(FISH_SIZE_DETAILS.values())
        feed_size = all_size[-1].feed_size

        for fish_size in all_size:
            if fish_size.min_size >= median_weight <= fish_size.max_size:
                return fish_size.feed_size

        return feed_size

    def get_appropriate_feed(self):
        """Get the appropriate feed in stock based on the median weight of the fishes"""
        size = self.get_feed_size()
        for f in self.farm.feeds:
            if f.size == size:
                return f

    def feed_fishes(self):
        """Feed the fishes in the pond"""
        self.log(f"Next feeding in {self.t_next_feeding * 24} hours")
        yield self.env.timeout(self.t_next_feeding)

        # select the appropriate feed
        feed = self.get_appropriate_feed()
        if feed == None:
            # buy feed
            self.log(f'Appropriate feed not found')
            feed_size = self.get_feed_size()
            feed = Feed(env=self.env, name=faker.name(), size=feed_size, verbose=False)
            self.farm.feeds.append(feed)

        # Get the feed to be consumed by each fish
        feed_weights = [
            f.get_hunger_weight() 
            for f in self.fishes
        ]
        total_feed = sum(feed_weights)

        # Should refill feed?
        remaining_feed = feed.get_quantity()
        if remaining_feed < total_feed:
            self.log(f'Feed not enough to for fishes')
            yield self.env.process(self.farm.stock_feed(feed=feed, weight=total_feed*2))

        # Update the feed stock
        self.log(f'Taking feed of weight: {total_feed}')
        yield self.env.process(feed.consume(total_feed))
            
        # Feed fishes and update their hunger
        self.log(f'Pour feed into pond')
        yield self.pond.feed.put(total_feed)

        # Update the next feed time
        self.t_next_feeding = self.get_next_feeding_time()

        # Log feeding data
        self.metric("feeding", {
            'time': self.env.now,
            'feed': feed.tag,
            'total_feed': total_feed,
        })

    def clean_pond(self):
        """Keep the pond healthy and secure for the fishes"""
        if self.pond.health.level < 50:
            self.log(f'Pond health is low, decontaminating')
            yield self.env.process(self.pond.decontaminate())
        yield self.env.timeout(1)
