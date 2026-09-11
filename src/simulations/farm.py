import statistics

import simpy
from typing_extensions import Literal
import numpy as np

from models.feed import FeedModel
from src.models.pond import PondModel
from src.models.farm import FarmModel
from simulations.cycle import Cycle
from src.simulations.feed import Feed
from src.utils.conversion import to_kobo, to_naira


class Farm(FarmModel):
    def __init__(self, env, name, money, ponds: list[PondModel]=[], feeds: list[FeedModel]=[], verbose = True):
        super().__init__(env, name, verbose)
        self.ponds = ponds
        self.feeds = feeds
        self.money = simpy.Container(env, init=to_kobo(money))

        self.data = {
            'transactions': [],
            'feed_stocking': [],
        }

        self.cycles: list[Cycle] = []

    def transact(self, action: Literal["credit", "debit"], amount, item, quantity=1.0):
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

    def feed_exists(self, size):
        """Check if the size of feed is available in stock"""
        for f in self.feeds:
            if f.size == size:
                return True
        return False
        
    def stock_feed_process(self, feed: Feed, weight):
        """Buy the feed for the fishes based on the current weight"""
        self.log(f"Stocking feed")        

        # Calculate the cost of the feed and pay for it
        feed_cost = feed.get_cost(weight)
        yield self.env.process(self.transact("debit", feed_cost, "feed", weight))
        feed.refill(weight)
        self.log(f"Stocked {weight}kg of feed")

        self.data['feed_stocking'].append({
            'time': self.env.now,
            'size': feed.size,
            'name': feed.name,
            'weight': weight,
            'cost': feed_cost
        })

    def actuire_pond(self):
        ...

    def start_cycle(self):
        ...
        