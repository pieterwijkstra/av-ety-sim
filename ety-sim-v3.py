# AV ETY Simulation v3: single load port, multiple discharge ports (variable distance), single vessel
import random
import pandas as pd

import salabim as sim

# Define parameters
SIM_DURATION = 7*10 # in days
CARGO_INTERVAL_LOWER = 2 # in days
CARGO_INTERVAL_UPPER = 3 # in days
LADEN_TRAVEL_TIME_MIN = 2 # in days
LADEN_TRAVEL_TIME_MAX = 3 # in days
LOAD_DISCHARGE_TIME = 0.5 # in days
BALLAST_TRAVEL_TIME_MIN = 0 # in days
BALLAST_TRAVEL_TIME_MAX = 1 # in days
CRUISE_SPEED = 15 # knots

# DISTANCES = pd.read_csv('distances.csv')
DISTANCES = pd.DataFrame([
    [0, 500, 200, 400, 300, 1000],
    [500, 0, 600, 800, 700, 1100],
    [200, 600, 0, 500, 300, 900],
    [400, 800, 500, 0, 100, 700],
    [300, 700, 300, 100, 0, 600],
    [1000, 1100, 900, 700, 600, 0]
    ],
    index=["Rotterdam", "Huelva", "Teeside", "Nynashamn", "Stenungsund", "Tornio"],
    columns=["Rotterdam", "Huelva", "Teeside", "Nynashamn", "Stenungsund", "Tornio"]
)

# Define components
class CargoGenerator(sim.Component):
    def process(self):
        while True: # Continuous loop
            discharge_ports = ["Teeside", "Stenungsund", "Nynashamn", "Huelva", "Tornio"]
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
        self.distance = DISTANCES.loc[load_port,discharge_port]

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
        travel_time_laden = self.cargo.distance/CRUISE_SPEED/24
        print("{:.2f} - {}: Departure laden to {} (Distance: {} NM, Travel time: {:.2f} days)".format(env.now(), self.name(), self.cargo.discharge_port, self.cargo.distance, travel_time_laden))
        yield self.hold(travel_time_laden)
        print("{:.2f} - {}: Arrive laden at {}".format(env.now(), self.name(), self.cargo.discharge_port))
        self.cargo.activate()
        print("{:.2f} - {}: Cargo discharged".format(env.now(), self.name()))


if __name__ == "__main__":

    env = sim.Environment(time_unit="days")
    env.time_to_str_format('{:10.2f}')

    CargoGenerator()
    vessel = Vessel(name="Coral A")
    cargo_queue = sim.Queue("cargo_queue")

    env.run(till=SIM_DURATION)
    print()
    cargo_queue.print_statistics()