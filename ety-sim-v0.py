# AV ETY Simulation v0: single load port, no laden, single vessel
import salabim as sim

class CargoGenerator(sim.Component):
    def process(self):
        while True: # Continuous loop
            Cargo()
            yield self.hold(sim.Uniform(2,3).sample())


class Cargo(sim.Component):
    def process(self):
        self.enter(cargo_queue)
        if vessel.ispassive():
            vessel.activate()
        yield self.passivate()

class Vessel(sim.Component):
    def process(self):
        while True: # Continuous loop
            while len(cargo_queue) == 0:
                yield self.passivate()
            self.cargo = cargo_queue.pop()
            yield self.hold(3)
            self.cargo.activate()


if __name__ == "__main__":

    env = sim.Environment(trace=True,time_unit="days")

    CargoGenerator()
    vessel = Vessel()
    cargo_queue = sim.Queue("cargo_queue")

    env.run(till=14)
    print()
    cargo_queue.print_statistics()