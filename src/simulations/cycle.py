from models.batch import BatchModel
from simulations.batch import Batch
from simulations.fish import Fish
from src.models.farm import FarmModel
from src.models.cycle import CycleModel, Phase, Stock
from src.models.animal import COST_PER_KILO, FISH_SIZE_DETAILS, AnimalModel, FishModel
from utils.conversion import to_kilo, to_kobo

class Cycle(CycleModel):
    """A full farming circle, from stocking to harvest"""
    def __init__(self, env, farm: FarmModel, stock: Stock):
        super().__init__(env, "Circle")
        self.farm = farm
        self.stock = stock
        self.fishes: list[FishModel] = []
        self.batches: list[BatchModel] = []

        # Start the stocking process
        self.current_phase = 0
        self.t_next_phase = 0
        self.next_harvest_rate = 0

        # self.existence = self.env.process(self.exist())

    def __str__(self):
        return f"""
        weight: {sum(f.weight.level for f in self.fishes)/len(self.fishes)}
        """

    def split_phase(self, phase: Phase):
        batches: list[list[FishModel]] = []
        n_fishes = len(self.fishes)
        n_batches = len(phase.fractions)

        for i in range(n_batches):
            start = int(sum(phase.fractions[0: i-1]) * n_fishes)
            stop = int(sum(phase.fractions[0: i]) * n_fishes)        
            batches.append(self.fishes[start: stop+1])
        return batches

    def run_phases(self):
        yield self.env.timeout(self.t_next_phase)

        phase = self.stock.phases[self.current_phase]
        self.next_harvest_rate = phase.harvest

        batches = self.split_phase(phase)
        for b in batches:
            pond = self.farm.get_appropriate_pond()
            avaliable_pond = self.farm.get_available_pond(pond.volume)

            if avaliable_pond != None:
                pond = avaliable_pond
            else:
                yield self.env.process(self.farm.acquire_pond(pond))

            batch = Batch(self.farm, pond, fishes=b, count=len(b), duration=phase.duration, stock_id=self.stock.id)
            self.batches.append(batch)

            self.current_phase += 1
            self.t_next_phase = phase.duration

    def stock_fishes(self):
        """Buy the fishes for the circle"""
        self.log(f"Waiting to stock fishes at {self.env.now}")
        yield self.env.timeout(self.rng.randint(1, 3))

        num_fishes = self.stock.count

        # Buy the fishes and pay for them
        fish_details = FISH_SIZE_DETAILS[self.stock.size]
        fish_size = self.rng.randint(fish_details.min_size, fish_details.max_size)
        cost_per_fish = to_kilo(fish_size) * COST_PER_KILO
        total_cost = to_kobo(num_fishes * cost_per_fish)
        yield self.env.process(self.farm.transact("debit", total_cost, "fishes", num_fishes))

        # Create the fishes and stock them in the pond
        self.fishes = [
            Fish(pond=self.farm.stocking_pond, id=id, type='Catfish', weight=self.rng.exponential(fish_size))
            for id in range(num_fishes)
        ]
        self.start_time = self.env.now

        yield self.env.process(self.run_phases())

    def harvest_fishes(self):
        """Harvest and sell the fishes to a buyer"""
        ...

    def exist(self):
        yield self.env.process(self.stock_fishes())
        while True:
            yield self.env.process(self.run_phases())
    