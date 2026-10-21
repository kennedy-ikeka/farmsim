import simpy
from typing_extensions import Literal
from datetime import datetime

from models.animal import FISH_SIZE_DETAILS, FISH_SIZES
from models.cycle import CycleModel
from models.feed import FeedModel
from models.simulation import SimulationModel
from simulations.pond import Pond
from src.models.pond import PondModel
from src.models.farm import FarmingModel, FarmModel
from simulations.cycle import Cycle
from utils.conversion import to_kilo
from utils.helper import get_param

class Farm(FarmModel):
    def __init__(self, sim: SimulationModel, name, id=0, farming_model = FarmingModel(), ponds: list[PondModel]=[], feeds: list[FeedModel]=[], verbose=0, active=True):
        super().__init__(sim, type="Farm", id=id, verbose=verbose, active=active)
        self.name = name
        self.ponds = ponds
        self.feeds = feeds
        self.money = simpy.Container(self.env, init=farming_model.capital) # in kobo
        self.cycles: list[CycleModel] = []
        self.farming_model = farming_model

        self.t_next_cycle = 0
        self.stocking_pond = Pond(sim, 1, 'Portable_Pond')

        self.existence = self.env.process(self.exist())

    def transact(self, action: Literal["credit", "debit"], amount: int, item: str, entity_tag: str, quantity=1.0):
        """Spend money from the circle"""
        yield self.env.timeout(0.1)    
            
        if action == "debit":
            yield self.money.get(amount)
        else:
            yield self.money.put(amount)

        self.metric("transactions", {
            'time': self.env.now,
            'action': action,
            'amount': amount,
            'item': item,
            'quantity': quantity,
            'entity': entity_tag,
            'balance': self.money.level
        })

    def feed_exists(self, size):
        """Check if the size of feed is available in stock"""
        for f in self.feeds:
            if f.size == size:
                return True
        return False
        
    def stock_feed(self, feed: FeedModel, weight: int):
        """Buy the feed for the fishes based on the current weight"""
        self.info(f"Stocking feed")        

        # Calculate the cost of the feed and pay for it
        feed_cost = feed.get_cost(weight)
        yield self.env.process(self.transact("debit", feed_cost, "feed", self.tag, weight))

        feed.refill(weight)
        in_stock = list(filter(lambda x: x.tag == feed.tag, self.feeds))
        if not len(in_stock):
            self.feeds.append(feed)
        
        self.metric("feed_stocking", {
            'size': feed.size,
            'name': feed.name,
            'weight': weight,
            'cost': feed_cost
        })

    def get_available_pond(self, volume):
        ponds: list[PondModel] = []
        for p in self.ponds:
            if p.volume >= volume and len(p.fishes) == 0:
                ponds.append(p)

        if len(ponds):
            ponds = sorted(ponds, key=lambda p: p.volume)
            return ponds[0]

        return None

    def generate_appropriate_pond(self, target_size: FISH_SIZES, count: int, duration: int) -> PondModel:
        target_weight = FISH_SIZE_DETAILS[target_size].max_size
        reqiured_biomass = to_kilo(target_weight * count)
        max_biomass_per_m3: int = get_param(self.farming_model.max_biomass_per_m3, target_weight) 
        required_volume = reqiured_biomass / max_biomass_per_m3
        dimension = required_volume ** (1/3)
        return Pond(sim=self.sim, id=len(self.ponds), type="Earthen_Pond", length=dimension, width=dimension, depth=dimension, duration=duration)

    def acquire_pond(self, pond: PondModel, renew=False):
        cost = pond.get_cost()
        yield self.env.process(self.transact('debit', cost, "pond", self.tag, pond.duration))

        pond.since = self.env.now
        if not renew:
            self.ponds.append(pond)

    def pond_subscription(self):
        while True:
            yield self.env.timeout(1)

            for p in self.ponds:
                # Is pond subscribable
                if p.duration == 0:
                    continue

                # Is subscription due
                used_rent = int(self.env.now - p.since)
                if used_rent <= p.duration:
                    continue
                
                # get the pond batch
                batches = [
                    batch for c in self.cycles 
                    for batch in c.batches 
                    if batch.active and batch.pond.tag == p.tag
                ]

                if len(batches) == 0:
                    self.ponds = list(filter(lambda x: x.tag != p.tag, self.ponds))
                    continue
                                
                # retain pond for extra duration
                yield self.env.process(self.acquire_pond(p, renew=True))       

    def run_next_cycle(self):
        """Initiate the next cycle"""        
        # Get the stock for the cycle
        stock = self.farming_model.stocks[0]

        # initiate the cycle
        cycle = Cycle(self.sim, self, stock, id=len(self.cycles))
        self.cycles.append(cycle)

        # move the stock to the buttom of the stock queue
        self.farming_model.stocks = self.farming_model.stocks[1:] + self.farming_model.stocks[:1]

        # set the next time for next cycle to start
        self.t_next_cycle = stock.gap if stock.gap != None else stock.duration
        yield self.env.timeout(self.t_next_cycle)    

    def exist(self):
        yield self.env.timeout(0)
        
        while self.active:
            yield self.env.process(self.run_next_cycle())

    def terminate(self):
        yield self.env.timeout(0)
        self.active = False
        