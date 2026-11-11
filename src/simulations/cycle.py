from pydantic import Field, computed_field
from simpy.events import EventCallback

from src.models.batch import BatchModel
from src.simulations.batch import Batch
from src.simulations.fish import Fish
from src.models.farm import FarmModel
from src.models.cycle import CycleModel, Phase
from src.models.fish import COST_PER_KILO, FISH_SIZE_DETAILS, FishModel
from src.utils.conversion import to_kilo, to_kobo, to_naira

class Cycle(CycleModel):
    fish_ids: list[str] = Field(default_factory=list, description="The fishes for the cycle")

    @computed_field
    @property
    def farm(self) -> FarmModel:
        return self.sim.get_asset("Farm", self.farm_id)

    @computed_field
    @property
    def fishes(self) -> list[FishModel]:
        return self.sim.list_assets("Fish", lambda x: x.id in self.fish_ids)
    
    """A full farming circle, from stocking to harvest"""
    def model_post_init(self, __context) -> None:
        super().model_post_init(__context)
        self.processes['existence'] = self.env.process(self.exist())

    def split_phase(self, phase: Phase):
        batches: list[list[FishModel]] = []
        n_fishes = len(self.fishes)

        cursor = int(0)
        fishes: list[FishModel] = sorted(self.fishes, key=lambda f: f.containers['weight'].level)

        for i in phase.fractions:
            stop = int(i * n_fishes) + cursor
            batches.append(fishes[cursor:stop])
            cursor = stop
        return batches

    def run_next_phase(self, issolated = False):
        while self.active or issolated:
            next_phase = len(self.batches)
            phase = self.stock.phases[next_phase]
            fish_batches = self.split_phase(phase)
            phase_batches: list[str] = []

            for b in fish_batches:
                pond = self.farm.generate_appropriate_pond(phase.target_size, len(b), phase.duration)
                avaliable_pond = self.farm.get_available_pond(pond.volume)

                if avaliable_pond != None:
                    pond = avaliable_pond
                else:
                    yield self.env.process(self.farm.acquire_pond(pond))

                cycles = self.sim.list_assets("Cycle", lambda c: getattr(c, 'id') in self.farm.cycle_ids)
                all_batches = [b for c in cycles for b in c.batches]
                batch_id = len(all_batches) + len(phase_batches)
                fish_ids = [f.id for f in b]
                batch = Batch(
                    sim=self.sim,
                    id=str(batch_id), 
                    farm_id=self.farm_id, 
                    pond_id=pond.id, 
                    fish_ids=fish_ids, 
                    duration=phase.duration, 
                    cycle_id=self.id
                )
                phase_batches.append(batch.id)

            self.batch_ids.append(phase_batches)
            yield self.env.timeout(phase.duration)
            yield self.env.process(self.harvest_fishes(phase.harvest))

            n_phases = len(self.stock.phases)
            n_batches = len(self.batches)
            if n_phases == n_batches:
                yield self.env.process(self.terminate())

    def stock_fishes(self):
        """Buy the fishes for the circle"""
        num_fishes = self.stock.count

        # Buy the fishes and pay for them
        fish_details = FISH_SIZE_DETAILS[self.stock.size]
        fish_size = self.rng.integers(fish_details.min_size, fish_details.max_size)
        total_weight = fish_size * num_fishes
        total_price = to_naira(num_fishes * fish_details.default_price)
        total_price_kobo = to_kobo(total_price)

        yield self.env.process(self.farm.transact("debit", total_price_kobo, "fishes", self.tag, num_fishes))

        # Create the fishes and stock them in the pond
        self.fish_ids = [
            Fish(
                sim=self.sim,
                pond_id=self.farm.stocking_pond.id, 
                id=str(id), 
                type='Catfish', 
                cycle_id=self.id, 
                farm_id=self.farm.id,
                options={"weight": self.rng.exponential(fish_size)}
            ).id
            for id in range(num_fishes)
        ]

        self.sim.add_metric("fish-stocks", self.farm_id, {
            "total_weight": round(total_weight, 2),
            "quantity": self.stock.count,
            "price": total_price_kobo,
            "cycle_id": self.id,
        })

    def harvest_fishes(self, fraction = 1.0):
        """Harvest and sell the fishes to a buyer"""
        yield self.env.timeout(0)

        fishes = sorted(self.fishes, key=lambda f: f.containers['weight'].level)
        num_harvest = int(fraction * len(self.fishes))
        to_harvest = fishes[:num_harvest]

        if len(to_harvest) == 0:
            return

        total_weight = sum(f.containers['weight'].level for f in to_harvest)
        total_price = to_naira(COST_PER_KILO * to_kilo(total_weight))
        total_price_kobo = to_kobo(total_price)

        yield self.env.process(self.farm.transact("credit", total_price_kobo, "fishes", self.tag, len(to_harvest)))
        self.sim.add_metric("fish-harvests", self.farm_id, {
            "total_weight": round(total_weight),
            "quantity": num_harvest,
            "price": total_price_kobo,
            "cycle_id": self.id,
        })

        for fish in to_harvest:
            yield self.env.process(fish.terminate())
        self.fish_ids = [f.id for f in fishes[num_harvest:]]

    def exist(self):
        self.start_time = self.env.now
        if self.active:
            self.env.process(self.schedule(self.stock.duration, self.terminate))

            yield self.env.process(self.stock_fishes())
            self.processes["run_phases"] = self.env.process(self.run_next_phase())      
        yield self.env.timeout(0)

    def terminate(self):
        yield self.env.process(self.harvest_fishes())
        self.active = False
        
        last_phase = self.batches[-1]   
        for b in last_phase:
            yield self.env.process(b.terminate())
