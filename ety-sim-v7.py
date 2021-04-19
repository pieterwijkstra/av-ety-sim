# AV ETY Simulation v7: Introduced realistic parameters + VRS, vessel assignment from passive vessels, first created (=alphabetical)
import random
import pandas as pd

import salabim as sim

# Define variable parameters
SIM_DURATION = 7*52 # in days
LOAD_DISCHARGE_TIME = 1.25 # in days
CRUISE_SPEED = 15 # knots
VRS = 8 # Percent

NO_OF_VESSELS = 6

BFB_CARGOES = 180 # per year

# Define constant parameters

LOAD_PORTS = {
    "Braefoot Bay": {
        "cargo_interval_mean": 365/BFB_CARGOES,
        "cargo_interval_std": 0.5,
        "discharge_ports": ["Antwerp"]
        },
    "Porvoo": {
        "cargo_interval_mean": 365/20,
        "cargo_interval_std": 5,
        "discharge_ports": ["Stenungsund", "Stenungsund", "Stade", "Stade", "Antwerp"]
    },
    "Rafnes": {
        "cargo_interval_mean": 365/78,
        "cargo_interval_std": 2,
        "discharge_ports": ["Antwerp", "Antwerp", "Antwerp", "Antwerp", "Antwerp", "Antwerp", "Stenungsund", "Stenungsund", "Stenungsund", "Stenungsund", "Stenungsund", "Stade", "Stade"]
    },
    "Le Havre": {
        "cargo_interval_mean": 365/9,
        "cargo_interval_std": 10,
        "discharge_ports": ["Antwerp"]
    },
}

DISTANCES = pd.DataFrame([
    [0, 435, 247, 1234, 572, 368, 570],
    [435, 0, 503, 1182, 486, 480, 517],
    [247, 503, 0, 1352, 687, 490, 688],
    [1234, 1182, 1352, 0, 796, 1047, 725],
    [572, 586, 687, 796, 0, 385, 112],
    [368, 480, 490, 1047, 385, 0, 383],
    [570, 517, 688, 725, 112, 383, 0]
    ],
    index=["Antwerp", "Braefoot Bay", "Le Havre", "Porvoo", "Rafnes", "Stade", "Stenungsund"],
    columns=["Antwerp", "Braefoot Bay", "Le Havre", "Porvoo", "Rafnes", "Stade", "Stenungsund"]
)

VESSELS = ["Coral Patula", "Coral Pearl", "Coral Alameda", "Coral Orinda", "Coral Favia", "Coral Fraseri", "Coral Fungia", "Coral Furcata", "Coral Shasta"]


# Define components
cargogenerators = {}


class CargoGenerator(sim.Component):
    def process(self):
        while True: # Continuous loop
            Cargo(load_port=self.load_port, discharge_port=random.choice(self.discharge_ports))
            yield self.hold(sim.Normal(mean=self.cargo_interval_mean, standard_deviation=self.cargo_interval_std).sample())

    def setup(self, load_port, parameters):
        self.load_port = load_port
        self.cargo_interval_mean = parameters["cargo_interval_mean"]
        self.cargo_interval_std = parameters["cargo_interval_std"]
        self.discharge_ports = parameters["discharge_ports"]


class Cargo(sim.Component):
    def process(self):
        self.enter(cargo_queue)
        for vessel in vessels:
            if vessel.ispassive():
                vessel.activate()
                break # activate 1 vessel only
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
        self.location = "Antwerp" #All vessels originate in Antwerp

    def execute_voyage(self):
        yield from self.ballast_leg()
        yield from self.load_cargo()
        yield from self.laden_leg()
        yield from self.discharge_cargo()

    def load_cargo(self):
        yield self.hold(LOAD_DISCHARGE_TIME)

    def discharge_cargo(self):
        self.location = self.cargo.discharge_port
        yield self.hold(LOAD_DISCHARGE_TIME)
        self.cargo.activate()
        print("{:.2f} - {}: {} discharged in {}".format(env.now(), self.name(), self.cargo.name(), self.location))

    def laden_leg(self):
        distance = DISTANCES.loc[self.cargo.load_port, self.cargo.discharge_port]
        travel_time_laden = distance / CRUISE_SPEED / 24 * ( 1 + VRS / 100 )
        print("{:.2f} - {}: {} loaded at {}, Departure laden to {}".format(env.now(), self.name(), self.cargo.name(),
                                                                              self.cargo.load_port,
                                                                              self.cargo.discharge_port))
        yield self.hold(travel_time_laden)
        print(
            "{:.2f} - {}: Arrive laden at {} (Distance: {} NM, Travel time: {:.2f} days)".format(env.now(), self.name(),
                                                                                                 self.cargo.discharge_port,
                                                                                                 distance,
                                                                                                 travel_time_laden))

    def ballast_leg(self):
        ballast_distance = DISTANCES.loc[self.location, self.cargo.load_port]
        travel_time_ballast = ballast_distance / CRUISE_SPEED / 24 * ( 1 + VRS / 100 )
        print("{:.2f} - {}: Departure ballast to {}".format(env.now(), self.name(), self.cargo.load_port))
        yield self.hold(travel_time_ballast)
        print("{:.2f} - {}: Arrive ballast at {} (Distance: {} NM, Travel time: {:.2f} days)".format(env.now(),
                                                                                                     self.name(),
                                                                                                     self.cargo.load_port,
                                                                                                     ballast_distance,
                                                                                                     travel_time_ballast))


def average_passive_time(components: list):
    total_time = 0
    no_components = len(components)
    for component in components:
        total_time += component.status.value_duration("passive")
    return total_time / no_components / SIM_DURATION


if __name__ == "__main__":

    env = sim.Environment(time_unit="days")
    env.time_to_str_format('{:10.2f}')

    vessels = [Vessel(name=name) for name in VESSELS[:NO_OF_VESSELS]]

    for load_port, parameters in LOAD_PORTS.items():
        cargogenerators[load_port] = CargoGenerator(load_port=load_port, parameters=parameters)

    cargo_queue = sim.Queue("cargo_queue")

    env.run(till=SIM_DURATION)
    print()
    cargo_queue.print_statistics()
    cargo_queue.print_histograms()
    cargo_queue.print_info()

    for vessel in vessels:
        vessel.status.print_histogram(values=True)

    print("Average idle time over vessels: {:.2%}".format(average_passive_time(vessels)))
