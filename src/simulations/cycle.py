import statistics

import numpy as np
from faker import Faker

from simulations.fish import Fish
from src.simulations.feed import Feed
from src.models.farm import FarmModel
from src.models.cycle import CycleModel
from src.models.pond import PondModel
from src.models.animal import AnimalModel


faker = Faker()

class Cycle(CycleModel):
    """A full farming circle, from stocking to harvest"""
    def __init__(self, env, farm: FarmModel, pond: PondModel, num_fishes: int, avg_weight: float):
        super().__init__(env, "Circle")
        self.farm = farm
        self.pond = pond
        self.t_next_feeding = float('inf')

        self.fishes: list[AnimalModel] = []

        # Start the stocking process
        self.stock_fishes_process = self.env.process(self.stock_fishes(num_fishes=num_fishes, avg_weight=avg_weight))
        self.data = {
            'feeding': [],
            'feed_conversion': [],
            'mortality': [],
            'maintainance': [],
        }

    def __str__(self):
        return f"""
        age: {self.get_age()},
        weight: {sum(f.weight.level for f in self.fishes)/len(self.fishes)}
        """

    def stock_fishes(self, num_fishes, avg_weight):
        """Buy the fishes for the circle"""
        self.log(f"Waiting to stock fishes at {self.env.now}")
        yield self.env.timeout(np.random.randint(1, 3))

        # Buy the fishes and pay for them
        cost_per_fish = np.random.uniform(25, 30)
        total_cost = num_fishes * cost_per_fish
        yield self.env.process(self.farm.transact("debit", total_cost, "fishes", num_fishes))

        # Create the fishes and stock them in the pond
        self.fishes = [
            Fish(pond=self.pond, id=id, weight=np.random.exponential(avg_weight), verbose=False)
            for id in range(num_fishes)
        ]
        self.start_time = self.env.now

        # Start the feeding process
        self.t_next_feeding = 1 # The next feeding time after fish stocking is 1 day
        yield self.env.process(self.feed_fishes())

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
        median_weight = statistics.median(f.weight.level for f in self.fishes)

        if median_weight < 0.005:
            return 0.8
        elif median_weight < 0.02:
            return 1.2
        elif median_weight < 0.05:
            return 1.5
        elif median_weight < 0.1:
            return 2.0
        elif median_weight < 0.25:
            return 3.0
        elif median_weight < 0.5:
            return 4.0
        elif median_weight < 0.8:
            return 5.0
        return 6.0

    def get_appropriate_feed(self):
        """Get the appropriate feed in stock based on the median weight of the fishes"""
        size = self.get_feed_size()
        for f in self.farm.feeds:
            if f.size == size:
                return f
            
    def get_age(self):
        """Get the age of this circle"""
        return int(self.env.now - self.start_time)

    def feed_fishes(self):
        """Feed the fishes in the pond"""
        while True:
            self.log(f"Next feeding in {self.t_next_feeding * 24} hours")
            yield self.env.timeout(self.t_next_feeding)

            # select the appropriate feed
            feed = self.farm.get_appropriate_feed()
            if feed == None:
                # buy feed
                self.log(f'Appropriate feed not found')
                feed_size = self.farm.get_feed_size()
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
                yield self.env.process(self.farm.stock_feed_process(feed=feed, weight=total_feed*2))

            # Update the feed stock
            self.log(f'Taking feed of weight: {total_feed}')
            yield self.env.process(feed.consume(total_feed))
                
            # Feed fishes and update their hunger
            self.log(f'Pour feed into pond')
            yield self.pond.feed.put(total_feed)

            # Update the next feed time
            self.t_next_feeding = self.get_next_feeding_time()

            # Log feeding data
            self.data['feeding'].append({
                'time': self.env.now,
                'feed': feed.tag,
                'total_feed': total_feed,
            })

    def clean_pond(self):
        """Keep the pond healthy and secure for the fishes"""
        while True:
            if self.pond.health.level < 50:
                self.log(f'Pond health is low, decontaminating')
                yield self.env.process(self.pond.decontaminate())
            yield self.env.timeout(1)

    def harvest_fishes(self):
        """Harvest and sell the fishes to a buyer"""
        ...
  