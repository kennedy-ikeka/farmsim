from typing_extensions import Optional

import simpy
import numpy as np
from math import sqrt

from src.models.animal import FISH_TYPES, FishModel, FISH_SIZE_DETAILS
from src.models.pond import PondModel
from utils.conversion import to_kilo

feeding_logs = []

class Fish(FishModel):
    """A fish entity in the the simulation"""

    def __init__(self, pond: PondModel, id: int, type: FISH_TYPES, weight: float, stock_id: Optional[int] = None, batch_id: Optional[int] = None, stomach=100, health=100, verbose=0, seed=0):
        super().__init__(pond.env, type=type, id=id, verbose=verbose, seed=seed)
        self.pond = pond
        self.type = type
        self.id = id
        self.weight = simpy.Container(pond.env, init=weight)
        self.stomach = simpy.Container(pond.env, capacity=100, init=stomach)
        self.health = simpy.Container(pond.env, capacity=100, init=health)
        self.stock_id = stock_id
        self.batch_id = batch_id
        self.active = True

        self.set_stomach_weight()
        self.pond.fishes.append(self)
        self.existence = self.env.process(self.exist())

    def __str__(self):
        return f"""
        id: {self.id},
        weight: {self.weight.level},
        health: {self.health.level}
        stomach_level: {self.stomach.level},
        stomach_weight: {self.stomach_weight},
        hunger_rate: {self.get_hunger_rate()},
        """

    def set_stomach_weight(self):
        all_sizes = list(FISH_SIZE_DETAILS.values())
        daily_feeding_ratio = all_sizes[-1].daily_feeding_ratio

        for fish_size in all_sizes:
            if fish_size.min_size <= self.weight.level < fish_size.max_size:
                daily_feeding_ratio = fish_size.daily_feeding_ratio
                break

        self.stomach_weight = daily_feeding_ratio * self.weight.level

    def get_hunger_rate(self):
        """Get the stomach level of the fish"""
        empty_stomach = self.stomach.capacity - self.stomach.level
        return empty_stomach / self.stomach.capacity

    def get_hunt_rate(self):
        """Get the hunt rate of the fish"""
        health_state = self.health.level / self.health.capacity
        return self.get_hunger_rate() * sqrt(self.weight.level) * health_state

    def get_feeding_rank(self) -> float:
        rates = sum(f.get_hunt_rate() for f in self.pond.fishes)
        if rates == 0:
            return 0
        hunt_rate = self.get_hunt_rate()
        return hunt_rate / rates

    def get_hunger_weight(self):
        """Get the maximum weight of feed it can consume at the moment"""
        hunger_rate = self.get_hunger_rate() 
        return hunger_rate * self.stomach_weight        

    def get_waste_weight(self):
        """Get the maximum weight of waste it can produce at the moment"""
        waste_rate = 1 - self.get_hunger_rate() 
        return waste_rate * self.stomach_weight

    def eat(self, feed_weight, fcr: float = 1):
        """Quench hunger by amount of feed"""
        if feed_weight <= 0:
            return

        hunger_level = self.stomach.capacity - self.stomach.level
        hunger_weight = self.get_hunger_weight()
        if hunger_weight <= 0:
            return
        
        can_eat = min(hunger_weight, feed_weight) # Can only eat as much as it is hungry
        quench_rate = can_eat / hunger_weight
        quench_level = quench_rate * hunger_level

        yield self.pond.feed.get(can_eat) # Catch feed
        self.info(f"Eat feed weighing {can_eat}")

        yield self.stomach.put(quench_level) # Quench hunger
        self.info(f"Quenched {((quench_level * 100)/self.stomach.capacity):.2f}% of hunger")

        weight_gained = can_eat/fcr
        yield self.weight.put(weight_gained) # Gain weight
        self.info(f"Gained weight by ({(weight_gained * 100)/self.weight.level:.2f}% )")

        self.metric("feeding", { 
            "id": self.id,
            "hunger_level": round(hunger_level),
            "hunger_weight": round(hunger_weight, 2),
            "feed_weight": round(can_eat, 2), 
            "quench_rate": round(quench_rate * 100),
            "stomach_level": round(self.stomach.level),
            "weight": round(self.weight.level),
            "stock_id": self.stock_id,
            "batch_id": self.batch_id
        })

    def hunt(self):
        """Hunt for food in the pond"""
        while self.active:
            t_hunt = self.rng.exponential(1/4)
            yield self.env.timeout(t_hunt)
            self.info(f"Hunting for food in the pond")

            feeding_rank = self.get_feeding_rank()        
            hunt_weight = self.pond.feed.level * feeding_rank

            self.info(f"Caught feed weighing {self.pond.feed.level}")
            yield self.env.process(self.eat(feed_weight=hunt_weight, fcr=1)) # Eat

    def excrete(self, excrete_weight):
        """Excrete waste"""
        if excrete_weight == 0:
            return
        
        waste_weight = self.get_waste_weight() 
        can_waste = min(waste_weight, excrete_weight)
        excrete_rate = can_waste / waste_weight
        excrete_level = excrete_rate * self.stomach.level

        yield self.stomach.get(excrete_level) # become hungrier
        self.info(f"Excreted, gained {((excrete_level * 100)/self.stomach.capacity):.2f}% of hunger")

        weight_lost = can_waste * excrete_rate * 0.01
        yield self.weight.get(weight_lost) # Lose weight
        self.info(f"Lost weight by ({(weight_lost * 100)/self.weight.level:.2f}% )")

        contamination_rate = (to_kilo(can_waste) ** (1/3)) / self.pond.volume
        health_lost = self.pond.health.level * contamination_rate
        if health_lost > 0:
            self.pond.health.get(health_lost)
        
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
        return np.mean([self.pond.health.level, self.health.level])

    def get_starving_rate(self):
        starving_rate = 0
        if self.stomach.level <= 1:
            feeding_history = self.tables.get('feeding', [])
            last_feed_at = feeding_history[-1]['time'] if len(feeding_history) else 0
            starving_rate = self.env.now - last_feed_at
        return starving_rate

    def get_overfeeding_rate(self):
        overfeeding_rate = 0
        overfeed_by = self.stomach.level - self.stomach.capacity
        if overfeed_by > 0:
            overfeeding_rate = (overfeed_by / self.stomach.capacity)
        return overfeeding_rate

    def stomach_health_effect(self):           
        overfeeding_rate = self.get_overfeeding_rate()
        starving_rate = self.get_starving_rate()

        rate = (starving_rate + overfeeding_rate) * 0.1
        return self.health.level * rate
    
    def health_check(self):        
        while self.active:
            t_health = self.rng.exponential(1)
            yield self.env.timeout(t_health)
            health = round(self.health.level, 5)
            pond_effect = self.pond_health_effect()
            stomach_effect = self.stomach_health_effect()
            new_health = round(pond_effect - stomach_effect, 5)
            shift = round(new_health - health, 5)
    
            if shift == 0:
                yield self.env.timeout(0)
            elif shift > 0:    
                self.info(f"Health: {health}, gained: {shift}")
                yield self.health.put(shift) 
            else:
                loss = min(np.abs(shift), health)
                self.info(f"Health: {health}, lost: {loss}")
                yield self.health.get(loss)
    
            if self.health.level == 0:
                yield self.env.process(self.terminate()) 
            
    def set_pond(self, pond: PondModel):
        self.pond = pond

    def exist(self):
        yield self.env.timeout(0)

        if self.active:
            self.health_process = self.env.process(self.health_check())
            self.hunt_process = self.env.process(self.hunt()) # hunt for feed
            self.digest_process = self.env.process(self.digest()) # excrete waste

    def terminate(self):
        yield self.env.timeout(0)
        self.active = False        
