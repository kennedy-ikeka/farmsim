import simpy
import numpy as np

from src.simulations.entity import Entity
from src.simulations.pond import Pond
from utils.conversion import to_grams

class Fish(Entity):
    """A fish entity in the the simulation"""
    def __init__(self, pond: Pond, id, weight, verbose=True):
        super().__init__(pond.env, name=f"Fish-{id}", verbose=verbose)
        self.pond = pond
        self.id = id
        self.weight = simpy.Container(pond.env, init=weight)
        self.stomach = simpy.Container(pond.env, capacity=100, init=np.random.uniform(0, 100))
        
        self.hunt_process = self.env.process(self.hunt()) # hunt for feed
        self.digest_process = self.env.process(self.digest()) # excrete waste

        self.pond.fishes.append(self)

    def __str__(self):
        return f"""
        id: {self.id},
        weight: {self.weight.level},
        stomach_level: {self.stomach.level},
        stomach_size: {self.get_stomach_size()},
        hunger_rate: {self.get_hunger_rate()},
        """

    def get_hunger_rate(self):
        """Get the stomach level of the fish"""
        empty_stomach = self.stomach.capacity - self.stomach.level
        return empty_stomach / self.stomach.capacity

    def get_stomach_size(self):
        """Get the stomach size with respect to the weight"""
        return self.weight.level * 0.1

    def get_hunger_weight(self):
        """Get the maximum weight of feed it can consume at the moment"""
        hunger_rate = self.get_hunger_rate() 
        stomach_size = self.get_stomach_size()
        return hunger_rate * stomach_size

    def get_waste_weight(self):
        """Get the maximum weight of waste it can produce at the moment"""
        waste_rate = 1 - self.get_hunger_rate() 
        stomach_size = self.get_stomach_size()
        return waste_rate * stomach_size

    def eat(self, feed_weight, fcr=1):
        """Quench hunger by amount of feed"""
        if feed_weight == 0:
            return
        
        hunger_weight = self.get_hunger_weight()
        quench_rate = feed_weight / hunger_weight
        quench_level = quench_rate * (self.stomach.capacity - self.stomach.level)

        yield self.stomach.put(quench_level) # Quench hunger
        self.log(f"Quenched {((quench_level * 100)/self.stomach.capacity):.2f}% of hunger")

        weight_gained = feed_weight/fcr
        yield self.weight.put(weight_gained) # Gain weight
        self.log(f"Gained weight by ({(weight_gained * 100)/self.weight.level:.2f}% )")

    def hunt(self):
        """Hunt for food in the pond"""
        while True:
            t_hunt = np.random.exponential(1/4)
            yield self.env.timeout(t_hunt)
            self.log(f"Hunting for food in the pond")

            quench_rate = np.random.uniform(0.8, 1) # It catches most of the feed
            hunger_weight = self.get_hunger_weight() 
            feed_weight = hunger_weight * quench_rate

            yield self.pond.feed.get(feed_weight) # Catch feed
            self.log(f"Caught feed weighing {feed_weight}")
            
            yield self.env.process(self.eat(feed_weight=feed_weight)) # Eat

    def excrete(self, excrete_weight):
        """Excrete waste"""
        if excrete_weight == 0:
            return
        
        waste_weight = self.get_waste_weight() 
        excrete_rate = excrete_weight / waste_weight
        excrete_level = excrete_rate * self.stomach.level

        yield self.stomach.get(excrete_level) # become hungrier
        self.log(f"Excreted, gained {((excrete_level * 100)/self.stomach.capacity):.2f}% of hunger")

        weight_lost = excrete_weight * excrete_rate
        yield self.weight.get(weight_lost) # Lose weight
        self.log(f"Lost weight by ({(weight_lost * 100)/self.weight.level:.2f}% )")

    def digest(self):
        """Release excrements after eating"""
        while True:
            t_excrete = np.random.exponential(1/3)
            yield self.env.timeout(t_excrete)

            excrement_rate = np.random.uniform(0.5, 1)
            waste_weight = self.get_waste_weight() 
            excrete_weight = waste_weight * excrement_rate

            yield self.env.process(self.excrete(excrete_weight=excrete_weight)) # Excrete

    def run(self, until=100):
        """Run the fish simulation"""
        self.env.run(until=until)
        