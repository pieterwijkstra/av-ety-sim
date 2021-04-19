# AV ETY Simulation v5: multiple load ports (independently generated), single vessel, varying discharge ports
import random
import pandas as pd

import salabim as sim

# Define parameters

SIM_DURATION = 7*10 # in days
CARGO_INTERVAL_LOWER = 5 # in days
CARGO_INTERVAL_UPPER = 6 # in days
LOAD_DISCHARGE_TIME = 0.5 # in days
CRUISE_SPEED = 15 # knots
LOAD_PORTS = ["Rotterdam", "Nynashamn"]

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
cargogenerators = {}


class CargoGenerator(sim.Component):
    def process(self):
        while True: # Continuous loop
            discharge_ports = ["Teeside", "Stenungsund", "Nynashamn", "Huelva", "Tornio"]
            Cargo(load_port=self.port, discharge_port=random.choice(discharge_ports))
            yield self.hold(sim.Uniform(CARGO_INTERVAL_LOWER,CARGO_INTERVAL_UPPER).sample())

    def setup(self, port):
        self.port = port

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

    def setup(self):
        self.location = "Rotterdam" #All vessels originate in Rotterdam

    def execute_voyage(self):
        ballast_distance = DISTANCES.loc[self.location, self.cargo.load_port]
        travel_time_ballast = ballast_distance / CRUISE_SPEED / 24
        print("{:.2f} - {}: Departure ballast to {}".format(env.now(), self.name(), self.cargo.load_port))
        yield self.hold(travel_time_ballast)
        print("{:.2f} - {}: Arrive ballast at {} (Distance: {} NM, Travel time: {:.2f} days)".format(env.now(), self.name(), self.cargo.load_port, ballast_distance, travel_time_ballast))
        yield self.hold(LOAD_DISCHARGE_TIME)
        distance = DISTANCES.loc[self.cargo.load_port,self.cargo.discharge_port]
        travel_time_laden = distance/CRUISE_SPEED/24
        print("{:.2f} - {}: Cargo loaded at {}, Departure laden to {}".format(env.now(), self.name(), self.cargo.load_port, self.cargo.discharge_port))
        yield self.hold(travel_time_laden)
        print("{:.2f} - {}: Arrive laden at {} (Distance: {} NM, Travel time: {:.2f} days)".format(env.now(), self.name(), self.cargo.discharge_port, distance, travel_time_laden))
        self.location = self.cargo.discharge_port
        yield self.hold(LOAD_DISCHARGE_TIME)
        self.cargo.activate()
        print("{:.2f} - {}: Cargo discharged".format(env.now(), self.name()))


if __name__ == "__main__":

    env = sim.Environment(time_unit="days")
    env.time_to_str_format('{:10.2f}')

    for port in LOAD_PORTS:
        cargogenerators[port] = CargoGenerator(port=port)

    vessel = Vessel(name="Coral A")
    cargo_queue = sim.Queue("cargo_queue")

    env.run(till=SIM_DURATION)
    print()
    cargo_queue.print_statistics()
    cargo_queue.print_histograms()
    cargo_queue.print_info()