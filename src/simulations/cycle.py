from datetime import datetime

from models.batch import BatchModel
from models.simulation import SimulationModel
from simulations.batch import Batch
from simulations.fish import Fish
from src.models.farm import FarmModel
from src.models.cycle import CycleModel, Phase, Stock
from src.models.animal import COST_PER_KILO, FISH_SIZE_DETAILS, FishModel
from utils.conversion import to_kilo, to_kobo, to_naira

class Cycle(CycleModel):
    """A full farming circle, from stocking to harvest"""
    def __init__(self, sim: SimulationModel, farm: FarmModel, stock: Stock, id: int, verbose=0, active=True) -> None:
        super().__init__(sim, type="Cycle", id=id, verbose=verbose, active=active)
        self.id = id
        self.farm = farm
        self.stock = stock
        self.fishes: list[FishModel] = []
        self.batches: list[list[BatchModel]] = []

        # Start the stocking process
        self.next_phase = 0
        self.next_harvest_rate = 0

        self.existence = self.env.process(self.exist())

    def __str__(self):
        fishes = []
        return f"""
        weight: {sum(f.weight.level for f in fishes)/len(fishes)}
        """

    def split_phase(self, phase: Phase):
        batches: list[list[FishModel]] = []
        n_fishes = len(self.fishes)

        cursor = int(0)
        fishes: list[FishModel] = sorted(self.fishes, key=lambda f: f.weight.level)

        for i in phase.fractions:
            stop = int(i * n_fishes) + cursor
            batches.append(fishes[cursor:stop])
            cursor = stop
        return batches

    def run_next_phase(self):
        phase = self.stock.phases[self.next_phase]
        fish_batches = self.split_phase(phase)
        phase_batches: list[BatchModel] = []
        for b in fish_batches:
            pond = self.farm.generate_appropriate_pond(phase.target_size, len(b), phase.duration)
            avaliable_pond = self.farm.get_available_pond(pond.volume)

            if avaliable_pond != None:
                pond = avaliable_pond
            else:
                yield self.env.process(self.farm.acquire_pond(pond))

            all_batches = [b for c in self.farm.cycles for b in c.batches]
            batch_id = len(all_batches) + len(phase_batches)
            batch = Batch(batch_id, self.farm, pond, fishes=b, duration=phase.duration, cycle_id=self.id)
            phase_batches.append(batch)

        self.batches.append(phase_batches)
        self.next_phase += 1
        self.next_harvest_rate = phase.harvest
        yield self.env.timeout(phase.duration)

    def stock_fishes(self):
        """Buy the fishes for the circle"""
        num_fishes = self.stock.count

        # Buy the fishes and pay for them
        fish_details = FISH_SIZE_DETAILS[self.stock.size]
        fish_size = self.rng.randint(fish_details.min_size, fish_details.max_size)
        total_weight = fish_size * num_fishes
        total_price = to_naira(to_kilo(total_weight) * COST_PER_KILO)
        total_price_kobo = to_kobo(total_price)

        yield self.env.process(self.farm.transact("debit", total_price_kobo, "fishes", self.tag, num_fishes))

        # Create the fishes and stock them in the pond
        self.fishes = [
            Fish(pond=self.farm.stocking_pond, id=id, type='Catfish', weight=self.rng.exponential(fish_size), stock_id=self.stock.id)
            for id in range(num_fishes)
        ]
        self.start_time = self.env.now
        self.active = True

        self.farm.metric("fish_stock", {
            "total_weight": round(total_weight, 2),
            "quantity": self.stock.count,
            "price": total_price_kobo,
            "cycle_id": self.id,
        })

    def harvest_fishes(self):
        """Harvest and sell the fishes to a buyer"""
        yield self.env.timeout(0)

        if self.next_harvest_rate == 0:
            return

        fishes = sorted(self.fishes, key=lambda f: f.weight.level)
        num_harvest = int(self.next_harvest_rate * len(self.fishes))
        to_harvest = fishes[:num_harvest]

        if len(to_harvest) == 0:
            return

        total_weight = sum(f.weight.level for f in to_harvest)
        total_price = to_naira(COST_PER_KILO * to_kilo(total_weight))
        total_price_kobo = to_kobo(total_price)

        yield self.env.process(self.farm.transact("credit", total_price_kobo, "fishes", self.tag, len(to_harvest)))
        self.farm.metric("fish_harvest", {
            "total_weight": round(total_weight),
            "quantity": num_harvest,
            "price": total_price_kobo,
            "cycle_id": self.id,
        })

        for fish in to_harvest:
            yield self.env.process(fish.terminate())
        self.fishes = fishes[num_harvest:]

    def exist(self):
        yield self.env.timeout(0)

        if self.active:
            yield self.env.process(self.stock_fishes())
            n_phases = len(self.stock.phases)

        while self.active:
            yield self.env.process(self.run_next_phase())
            yield self.env.process(self.harvest_fishes())

            if self.next_phase == n_phases:
                yield self.env.process(self.terminate()) 

    def terminate(self):
        self.active = False
        self.next_harvest_rate = 1
        yield self.env.process(self.harvest_fishes())
