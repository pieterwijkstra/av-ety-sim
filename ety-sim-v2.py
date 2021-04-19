# AV ETY Simulation v2: single load port, multiple discharge ports (equal distance), single vessel
import random

import salabim as sim

# Define parameters
CARGO_INTERVAL_LOWER = 2
CARGO_INTERVAL_UPPER = 3
LADEN_TRAVEL_TIME_MIN = 2
LADEN_TRAVEL_TIME_MAX = 3
LOAD_DISCHARGE_TIME = 0.5
BALLAST_TRAVEL_TIME_MIN = 0
BALLAST_TRAVEL_TIME_MAX = 1


# Define components
class CargoGenerator(sim.Component):
    def process(self):
        while True: # Continuous loop
            discharge_ports = ["Teeside", "Stenungsund", "Nynashamn", "Huelva"]
            Cargo(load_port="Rotterdam", discharge_port=random.choice(discharge_ports))
            yield self.hold(sim.Uniform(CARGO_INTERVAL_LOWER,CARGO_INTERVAL_UPPER).sample())


class Cargo(sim.Component):
    def process(self):
        self.enter(cargo_queue)
        if vessel.ispassive():
            vessel.activate()
        yield self.passivate()

    def setup(self, load_port, discharge_port):
        self.load_port = load_port
        self.discharge_port = discharge_port

class Vessel(sim.Component):
    def process(self):
        while True: # Continuous loop
            while len(cargo_queue) == 0:
                yield self.passivate()
            self.cargo = cargo_queue.pop()
            yield from self.execute_voyage()

    def execute_voyage(self):
        print("{:.2f} - {}: Departure ballast to {}".format(env.now(), self.name(), self.cargo.load_port))
        yield self.hold(sim.Uniform(BALLAST_TRAVEL_TIME_MIN, BALLAST_TRAVEL_TIME_MAX).sample())
        print("{:.2f} - {}: Arrive ballast at {}".format(env.now(), self.name(), self.cargo.load_port))
        yield self.hold(LOAD_DISCHARGE_TIME)
        print("{:.2f} - {}: Cargo loaded at {}".format(env.now(), self.name(), self.cargo.load_port))
        print("{:.2f} - {}: Departure laden to {}".format(env.now(), self.name(), self.cargo.discharge_port))
        yield self.hold(sim.Uniform(LADEN_TRAVEL_TIME_MIN, LADEN_TRAVEL_TIME_MAX).sample())
        print("{:.2f} - {}: Arrive laden at {}".format(env.now(), self.name(), self.cargo.discharge_port))
        self.cargo.activate()
        print("{:.2f} - {}: Cargo discharged".format(env.now(), self.name()))


if __name__ == "__main__":

    env = sim.Environment(time_unit="days")
    env.time_to_str_format('{:10.2f}')

    CargoGenerator()
    vessel = Vessel(name="Coral A")
    cargo_queue = sim.Queue("cargo_queue")

    env.run(till=14)
    print()
    cargo_queue.print_statistics()