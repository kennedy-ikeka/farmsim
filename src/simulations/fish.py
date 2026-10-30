from pydantic import Field, computed_field
from simpy import Container
import numpy as np

from src.models.fish import FishModel, FISH_SIZE_DETAILS
from src.models.pond import PondModel
from src.utils.conversion import to_kilo

feeding_logs = []

class Fish(FishModel):
    """A fish entity in the the simulation"""

    @computed_field
    @property
    def pond(self) -> PondModel:
        return self.sim.assets['Pond'][self.pond_id]

    def model_post_init(self, __context):
        super().model_post_init(__context)
        self.containers["weight"] = Container(self.env, init=self.options.get('weight', self.rng.integers(0, 2000)))
        self.containers["stomach"] = Container(self.env, capacity=100, init=self.options.get('stomach', 100))
        self.containers["health"] = Container(self.env, capacity=100, init=self.options.get('health', 100))

        self.set_stomach_weight()
        self.pond.fishes.append(self)
        self.processes['existence'] = self.env.process(self.exist())

    def set_stomach_weight(self):
        all_sizes = list(FISH_SIZE_DETAILS.values())
        daily_feeding_ratio = all_sizes[-1].daily_feeding_ratio

        for fish_size in all_sizes:
            if fish_size.min_size <= self.containers['weight'].level < fish_size.max_size:
                daily_feeding_ratio = fish_size.daily_feeding_ratio
                break

        self._stomach_weight = daily_feeding_ratio * self.containers['weight'].level

    def get_hunger_rate(self):
        """Get the stomach level of the fish"""
        empty_stomach = self.containers['stomach'].capacity - self.containers['stomach'].level
        return empty_stomach / self.containers['stomach'].capacity

    def get_hunt_rate(self):
        """Get the hunt rate of the fish"""
        health_state = self.containers['health'].level / self.containers['health'].capacity
        return self.get_hunger_rate() * np.sqrt(self.containers['weight'].level) * health_state

    def get_feeding_rank(self) -> float:
        rates = sum(f.get_hunt_rate() for f in self.pond.fishes)
        if rates == 0:
            return 0
        hunt_rate = self.get_hunt_rate()
        return hunt_rate / rates

    def get_hunger_weight(self):
        """Get the maximum weight of feed it can consume at the moment"""
        hunger_rate = self.get_hunger_rate() 
        return hunger_rate * self._stomach_weight        

    def get_waste_weight(self):
        """Get the maximum weight of waste it can produce at the moment"""
        waste_rate = 1 - self.get_hunger_rate() 
        return waste_rate * self._stomach_weight

    def eat(self, feed_weight, fcr: float = 1):
        """Quench hunger by amount of feed"""
        if feed_weight <= 0:
            return

        hunger_level = self.containers['stomach'].capacity - self.containers['stomach'].level
        hunger_weight = self.get_hunger_weight()
        if hunger_weight <= 0:
            return
        
        can_eat = min(hunger_weight, feed_weight) # Can only eat as much as it is hungry
        quench_rate = can_eat / hunger_weight
        quench_level = quench_rate * hunger_level

        yield self.pond.containers['feed'].get(can_eat) # Catch feed
        self.info(f"Eat feed weighing {can_eat}")

        yield self.containers['stomach'].put(quench_level) # Quench hunger
        self.info(f"Quenched {((quench_level * 100)/self.containers['stomach'].capacity):.2f}% of hunger")

        weight_gained = can_eat/fcr
        yield self.containers['weight'].put(weight_gained) # Gain weight
        self.info(f"Gained weight by ({(weight_gained * 100)/self.containers['weight'].level:.2f}% )")

        self.metric("feeding", { 
            "id": self.id,
            "hunger_level": round(hunger_level),
            "hunger_weight": round(hunger_weight, 2),
            "feed_weight": round(can_eat, 2), 
            "quench_rate": round(quench_rate * 100),
            "stomach_level": round(self.containers['stomach'].level),
            "weight": round(self.containers['weight'].level),
            "stock_id": self.cycle_id,
            "batch_id": self.batch_id,
            "farm_id": self.farm_id
        })

    def hunt(self):
        """Hunt for food in the pond"""
        while self.active:
            t_hunt = self.rng.exponential(1/4)
            yield self.env.timeout(t_hunt)
            self.info(f"Hunting for food in the pond")

            feeding_rank = self.get_feeding_rank()        
            hunt_weight = self.pond.containers['feed'].level * feeding_rank

            self.info(f"Caught feed weighing {self.pond.containers['feed'].level}")
            yield self.env.process(self.eat(feed_weight=hunt_weight, fcr=1)) # Eat

    def excrete(self, excrete_weight):
        """Excrete waste"""
        if excrete_weight == 0:
            return
        
        waste_weight = self.get_waste_weight() 
        can_waste = min(waste_weight, excrete_weight)
        excrete_rate = can_waste / waste_weight
        excrete_level = excrete_rate * self.containers['stomach'].level

        yield self.containers['stomach'].get(excrete_level) # become hungrier
        self.info(f"Excreted, gained {((excrete_level * 100)/self.containers['stomach'].capacity):.2f}% of hunger")

        weight_lost = can_waste * excrete_rate * 0.01
        yield self.containers['weight'].get(weight_lost) # Lose weight
        self.info(f"Lost weight by ({(weight_lost * 100)/self.containers['weight'].level:.2f}% )")

        contamination_rate = (to_kilo(can_waste) ** (1/3)) / self.pond.volume
        health_lost = self.pond.containers['health'].level * contamination_rate
        if health_lost > 0:
            self.pond.containers['health'].get(health_lost)
        
    def digest(self):
        """Release excrements after eating"""
        while self.active:
            t_excrete = self.rng.exponential(1/12)
            yield self.env.timeout(t_excrete)

            digestion_rate = self.rng.uniform(0.5, .8)
            waste_weight = self.get_waste_weight() 
            excrete_weight = waste_weight * digestion_rate

            yield self.env.process(self.excrete(excrete_weight=excrete_weight)) # Excrete
            self.set_stomach_weight()

    def pond_health_effect(self):
        return np.mean([self.pond.containers['health'].level, self.containers['health'].level])

    def get_starving_rate(self):
        starving_rate = 0
        if self.containers['stomach'].level <= 1:
            feeding_history = self.tables.get('feeding', [])
            last_feed_at = feeding_history[-1]['time'] if len(feeding_history) else 0
            starving_rate = self.env.now - last_feed_at
        return starving_rate

    def get_overfeeding_rate(self):
        overfeeding_rate = 0
        overfeed_by = self.containers['stomach'].level - self.containers['stomach'].capacity
        if overfeed_by > 0:
            overfeeding_rate = (overfeed_by / self.containers['stomach'].capacity)
        return overfeeding_rate

    def stomach_health_effect(self):           
        overfeeding_rate = self.get_overfeeding_rate()
        starving_rate = self.get_starving_rate()

        rate = (starving_rate + overfeeding_rate) * 0.1
        return self.containers['health'].level * rate
    
    def health_check(self):        
        while self.active:
            t_health = self.rng.exponential(1)
            yield self.env.timeout(t_health)
            health = round(self.containers['health'].level, 5)
            pond_effect = self.pond_health_effect()
            stomach_effect = self.stomach_health_effect()
            new_health = round(pond_effect - stomach_effect, 5)
            shift = round(new_health - health, 5)
    
            if shift == 0:
                yield self.env.timeout(0)
            elif shift > 0:    
                self.info(f"Health: {health}, gained: {shift}")
                yield self.containers['health'].put(shift) 
            else:
                loss = min(np.abs(shift), health)
                self.info(f"Health: {health}, lost: {loss}")
                yield self.containers['health'].get(loss)
    
            if self.containers['health'].level == 0:
                yield self.env.process(self.terminate()) 

    def exist(self):
        yield self.env.timeout(0)

        if self.active:
            self.processes['health'] = self.env.process(self.health_check())
            self.processes['hunt'] = self.env.process(self.hunt()) # hunt for feed
            self.processes['digest'] = self.env.process(self.digest()) # excrete waste

    def terminate(self):
        yield self.env.timeout(0)
        self.active = False        
