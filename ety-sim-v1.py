# AV ETY Simulation v1: single load port, laden travel, single vessel
import salabim as sim

# Define parameters
CARGO_INTERVAL_LOWER = 2
CARGO_INTERVAL_UPPER = 3
LADEN_TRAVEL_TIME_MIN = 2
LADEN_TRAVEL_TIME_MAX = 3
BALLAST_TRAVEL_TIME_MIN = 0
BALLAST_TRAVEL_TIME_MAX = 1


# Define components
class CargoGenerator(sim.Component):
    def process(self):
        while True: # Continuous loop
            Cargo()
            yield self.hold(sim.Uniform(CARGO_INTERVAL_LOWER,CARGO_INTERVAL_UPPER).sample())


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
            print("Departure ballast to load port")
            yield self.hold(sim.Uniform(BALLAST_TRAVEL_TIME_MIN, BALLAST_TRAVEL_TIME_MAX).sample())
            print("Arrive ballast at load port")
            self.cargo = cargo_queue.pop()
            print("Cargo loaded")
            print("Departure laden load port")
            yield self.hold(sim.Uniform(LADEN_TRAVEL_TIME_MIN, LADEN_TRAVEL_TIME_MAX).sample())
            print("Arrive laden discharge port")
            self.cargo.activate()
            print("Cargo discharged")


if __name__ == "__main__":

    env = sim.Environment(trace=True,time_unit="days")

    CargoGenerator()
    vessel = Vessel()
    cargo_queue = sim.Queue("cargo_queue")

    env.run(till=14)
    print()
    cargo_queue.print_statistics()