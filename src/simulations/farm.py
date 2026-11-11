from pydantic import Field
from simpy import Container
from typing_extensions import Literal

from src.models.fish import FISH_SIZE_DETAILS, FISH_SIZES
from src.models.feed import FeedModel
from src.simulations.pond import Pond
from src.models.pond import PondModel
from src.models.farm import FarmModel
from src.simulations.cycle import Cycle
from src.utils.conversion import to_kilo
from src.utils.helper import get_param

class Farm(FarmModel):
    stocking_pond: Pond = Field(default_factory=lambda data: Pond(sim=data["sim"], type="Portable_Pond"), description="The ponds stocking portable pond")

    def model_post_init(self, __context):
        super().model_post_init(__context)

        self.business_model.stocks.sort(key=lambda s: s.id)
        self.containers['money'] = Container(self.env, init=self.business_model.capital) # in kobo
        self.processes['existence'] = self.env.process(self.exist())

    def transact(self, action: Literal["credit", "debit"], amount: int, item: str, entity_tag: str, quantity=1.0):
        """Spend money from the circle"""
        yield self.env.timeout(0.1)    
            
        if action == "debit":
            yield self.containers['money'].get(amount)
        else:
            yield self.containers['money'].put(amount)

        self.sim.add_metric("transactions", self.id, {
            'time': self.env.now,
            'action': action,
            'amount': amount,
            'item': item,
            'quantity': quantity,
            'entity': entity_tag,
            'balance': self.containers['money'].level
        })

    def feed_exists(self, size):
        """Check if the size of feed is available in stock"""
        feeds = self.sim.list_assets("Feed", lambda c: getattr(c, 'id') in self.feed_ids)
        for f in feeds:
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
        feeds = self.sim.list_assets("Feed", lambda c: getattr(c, 'id') in self.feed_ids)
        in_stock = list(filter(lambda x: x.tag == feed.tag, feeds))
        if not len(in_stock):
            self.feed_ids.append(feed.id)
        
        self.sim.add_metric("feed-stocks", self.id, {
            'size': feed.size,
            'name': feed.name,
            'weight': weight,
            'cost': feed_cost
        })

    def get_available_pond(self, volume):
        ponds: list[PondModel] = []
        farm_ponds = self.sim.list_assets("Pond", lambda c: getattr(c, 'id') in self.pond_ids)
        for p in farm_ponds:
            if p.volume >= volume and len(p.fish_ids) == 0:
                ponds.append(p)

        if len(ponds):
            ponds = sorted(ponds, key=lambda p: p.volume)
            return ponds[0]

        return None

    def generate_appropriate_pond(self, target_size: FISH_SIZES, count: int, duration: int) -> PondModel:
        target_weight = FISH_SIZE_DETAILS[target_size].max_size
        reqiured_biomass = to_kilo(target_weight * count)
        max_biomass_per_m3: int = get_param(self.business_model.max_biomass_per_m3, target_weight) 
        required_volume = reqiured_biomass / max_biomass_per_m3
        dimension = required_volume ** (1/3)
        id = len(self.pond_ids)
        return Pond(sim=self.sim, id=str(id), type="Earthen_Pond", length=dimension, width=dimension, depth=dimension, duration=duration)

    def acquire_pond(self, pond: PondModel, renew=False):
        cost = pond.get_cost()
        yield self.env.process(self.transact('debit', cost, "pond", self.tag, pond.duration))

        pond.acquired_at = self.env.now
        if not renew:
            self.pond_ids.append(pond.id)

    def pond_subscription(self, issolated=False):
        while self.active or issolated:
            yield self.env.timeout(1)

            # for p in self.ponds:
            #     # Is pond subscribable
            #     if p.duration == 0:
            #         continue

            #     if p.acquired_at is None:
            #         continue

            #     # Is subscription due
            #     used_rent = int(self.env.now - p.acquired_at)
            #     if used_rent <= p.duration:
            #         continue
                
            #     # get the pond batch
            #     batches = [
            #         batch for c in self.cycles 
            #         for phase_batches in c.batches 
            #         for batch in phase_batches
            #         if batch.active and batch.pond.tag == p.tag
            #     ]

            #     if len(batches) == 0:
            #         self.ponds = list(filter(lambda x: x.tag != p.tag, self.ponds))
            #         continue
                                
            #     # retain pond for extra duration
            #     yield self.env.process(self.acquire_pond(p, renew=True))       

    def run_next_cycle(self, issolated=False):
        """Initiate the next cycle"""        
        # Get the stock for the cycle        
        while self.active or issolated:
            cycles = self.sim.list_assets("Cycle", lambda c: getattr(c, 'id') in self.cycle_ids)
            active_cycles = [c for c in cycles if c.active]
            stock = self.business_model.stocks[0]
            active_stock_cycles = [c for c in active_cycles if c.stock.id == stock.id]

            if len(active_stock_cycles) and stock.gap == 0:
                last_stock_cycle = active_stock_cycles[-1]
                wait = stock.duration - last_stock_cycle.get_age() 
                wait = wait if wait > 0 else 1
                yield self.env.timeout(wait)
                continue

            # initiate the cycle
            id = len(self.cycle_ids) + 1
            cycle = Cycle(sim=self.sim,farm_id=self.id, stock=stock, id=str(id), verbose=3)
            self.cycle_ids.append(cycle.id)

            # move the stock to the buttom of the stock queue
            self.business_model.stocks = self.business_model.stocks[1:] + self.business_model.stocks[:1]

            # set the next time for next cycle to start
            t_next_cycle = stock.gap if stock.gap is not None else stock.duration
            yield self.env.timeout(t_next_cycle)    

    def exist(self):
        yield self.env.timeout(0)

        if self.active:
            self.processes['pond_subscription'] = self.env.process(self.pond_subscription())
            self.processes['run_cycle'] = yield self.env.process(self.run_next_cycle())

    def terminate(self):
        yield self.env.timeout(0)
        self.active = False
        