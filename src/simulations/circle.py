from typing_extensions import Literal

import simpy
import numpy as np
import statistics

from src.utils.conversion import to_kobo, to_naira
from src.simulations.entity import Entity
from src.simulations.feed import Feed
from src.simulations.fish import Fish


class Circle(Entity):
    """A full farming circle, from stocking to harvest"""
    def __init__(self, env, money, pond, num_fishes, avg_weight, feeds: list[Feed]=[]):
        super().__init__(env, name="Circle")
        self.money = simpy.Container(env, init=to_kobo(money))
        self.pond = pond
        self.feeds= feeds
        self.t_next_feeding = float('inf')

        # Start the stocking process
        self.env.process(self.stock_fishes_process(num_fishes=num_fishes, avg_weight=avg_weight))
        self.data = {
            'transactions': [],
            'feeding': [],
            'feed_conversion': [],
            'feed_stocking': [],
            'mortality': [],
            'maintainance': [],
        }

    def stock_fishes_process(self, num_fishes, avg_weight):
        """Buy the fishes for the circle"""
        self.log(f"Waiting to stock fishes at {self.env.now}")
        yield self.env.timeout(np.random.randint(1, 3))

        # Buy the fishes and pay for them
        cost_per_fish = np.random.uniform(25, 30)
        total_cost = num_fishes * cost_per_fish
        yield self.env.process(self.transact("debit", total_cost, "fishes", num_fishes))

        # Create the fishes and stock them in the pond
        self.fishes = [
            Fish(pond=self.pond, id=id, weight=np.random.exponential(avg_weight), verbose=False)
            for id in range(num_fishes)
        ]
        self.start_time = self.env.now

        # Start the feeding process
        self.t_next_feeding = 1 # The next feeding time after fish stocking is 1 day
        yield self.env.process(self.feed_fishes_process())

    def transact(self, action: Literal["credit", "debit"], amount, item, quantity=1):
        """Spend money from the circle"""
        kobo_amount = to_kobo(amount)
        if action == "debit":
            yield self.money.get(kobo_amount)
        else:
            yield self.money.put(kobo_amount)

        self.log(f"{action.capitalize()} {to_naira(kobo_amount)}: {item} x {quantity}")
        self.data['transactions'].append({
            'time': self.env.now,
            'action': action,
            'amount': kobo_amount,
            'item': item,
            'quantity': quantity
        })

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

    def get_age(self):
        """Get the age of this circle"""
        return int(self.env.now - self.start_time)

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
        for f in self.feeds:
            if f.size == size:
                return f

    def feed_exists(self, size):
        """Check if the size of feed is available in stock"""
        for f in self.feeds:
            if f.size == size:
                return True
        return False

    def stock_feed_process(self, size):
        """Buy the feed for the fishes based on the current weight"""
        self.log(f"Stocking feed")

        # Get the feed to be stocked
        quantity = 1
        feed = Feed(env=self.env, name='A', size=size, quantity=quantity)

        # Calculate the cost of the feed and pay for it
        feed_cost = feed.cost * quantity
        self.feeds.append(feed)
        yield self.env.process(self.transact("debit", feed_cost, "feed", quantity))
        self.log(f"Stocked feed for {to_naira(feed_cost)}")

        self.data['feed_stocking'].append({
            'time': self.env.now,
            'size': size,
            'name': feed.name,
            'quantity': quantity,
            'cost': feed_cost
        })

    def feed_fishes_process(self):
        """Feed the fishes in the pond"""
        while True:
            self.log(f"Next feeding in {self.t_next_feeding * 24} hours")
            yield self.env.timeout(self.t_next_feeding)

            # select the appropriate feed
            feed = self.get_appropriate_feed()
            if feed == None:
                # buy feed
                self.log(f'Appropriate feed not found')
                feed_size = self.get_feed_size()
                yield self.env.process(self.stock_feed_process(size=feed_size))
                feed = self.get_appropriate_feed()

            # Get the feed to be consumed by each fish
            feed_weights = [
                f.get_feed_weight() 
                for f in self.fishes
            ]
            total_feed = sum(feed_weights)

            # Should refill feed?
            if feed.stock.level < total_feed:
                self.log(f'Feed not enough to for fishes')
                yield self.env.process(self.stock_feed_process(size=feed.size))

            # Update the feed stock
            self.log(f'Taking feed of weight: {total_feed}')
            yield self.env.process(feed.take(total_feed))
                
            # Feed fishes and update their hunger
            self.log(f'Feeding fishes')
            yield self.env.all_of([
                self.env.process(f.eat(weight=w, fcr=1))
                for f, w in zip(self.fishes, feed_weights)
            ])

            # Update the next feed time
            self.t_next_feeding = self.get_next_feeding_time()

            self.data['feeding'].append({
                'time': self.env.now,
                'feed': feed.tag,
                'total_feed': total_feed,
            })

    def maintain_pond_process(self):
        """Keep the pond healthy and secure for the fishes"""
        while True:
            if self.pond.health.level < 50:
                self.log(f'Pond health is low, decontaminating')
                yield self.env.process(self.pond.decontaminate())
            yield self.env.timeout(1)

    def harvest_process(self):
        """Harvest and sell the fishes to a buyer"""
        ...

    def run(self, until):
        """Run the circle"""
        self.env.run(until=until)
        