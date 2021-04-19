# AV ETY Simulation v9: Added Loops, introduced realistic parameters + VRS, vessel assignment from passive vessels, first created (=alphabetical)
import random
import pandas as pd

import salabim as sim

# Define variable parameters
SIM_DURATION = 365 # in days
LOAD_DISCHARGE_TIME = 1.25 # in days
CRUISE_SPEED = 15 # knots
VRS = 8 # Percent

NO_OF_VESSELS = [7, 6, 5 ]
BFB_CARGOES = [120, 150, 180] # per year
MEAN_PORT_DISRUPT_VALUES = [0, 0.25]
CRUISE_SPEEDS = [15, 12] # knots


# Define constant parameters

def load_ports(bfb_cargoes):
    return {
        "Braefoot Bay": {
            "cargo_interval_mean": 365/bfb_cargoes,
            "cargo_interval_std": 0.5,
            "discharge_ports": ["Antwerp"]
            },
        "Porvoo": {
            "cargo_interval_mean": 365/20,
            "cargo_interval_std": 3,
            "discharge_ports": ["Stenungsund", "Stenungsund", "Stade", "Stade", "Antwerp"]
        },
        "Rafnes": {
            "cargo_interval_mean": 365/78,
            "cargo_interval_std": 1,
            "discharge_ports": ["Antwerp", "Antwerp", "Antwerp", "Antwerp", "Antwerp", "Antwerp", "Stenungsund", "Stenungsund", "Stenungsund", "Stenungsund", "Stenungsund", "Stade", "Stade"]
        },
        "Le Havre": {
            "cargo_interval_mean": 365/9,
            "cargo_interval_std": 5,
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

VESSELS = ["Coral Lophelia", "Coral Parensis", "Coral Patula", "Coral Pearl", "Coral Alameda", "Coral Orinda", "Coral Shasta", "Coral Furcata", "Coral Fraseri", "Coral Fungia"]


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
        port_time = LOAD_DISCHARGE_TIME + sim.Normal(MEAN_PORT_DISRUPT, 0.25)
        yield self.hold(port_time)

    def discharge_cargo(self):
        self.location = self.cargo.discharge_port
        port_time = LOAD_DISCHARGE_TIME + sim.Normal(MEAN_PORT_DISRUPT, 0.25)
        yield self.hold(port_time)
        self.cargo.activate()
        log_file.write("{:.2f} - {}: {} discharged in {} \n".format(env.now(), self.name(), self.cargo.name(), self.location))

    def laden_leg(self):
        distance = DISTANCES.loc[self.cargo.load_port, self.cargo.discharge_port]
        travel_time_laden = distance / CRUISE_SPEED / 24 * ( 1 + VRS / 100 )
        log_file.write("{:.2f} - {}: {} loaded at {}, Departure laden to {} \n".format(env.now(), self.name(), self.cargo.name(),
                                                                              self.cargo.load_port,
                                                                              self.cargo.discharge_port))
        yield self.hold(travel_time_laden)
        log_file.write(
            "{:.2f} - {}: Arrive laden at {} (Distance: {} NM, Travel time: {:.2f} days) \n".format(env.now(), self.name(),
                                                                                                 self.cargo.discharge_port,
                                                                                                 distance,
                                                                                                 travel_time_laden))

    def ballast_leg(self):
        ballast_distance = DISTANCES.loc[self.location, self.cargo.load_port]
        travel_time_ballast = ballast_distance / CRUISE_SPEED / 24 * ( 1 + VRS / 100 )
        log_file.write("{:.2f} - {}: Departure ballast to {} \n".format(env.now(), self.name(), self.cargo.load_port))
        yield self.hold(travel_time_ballast)
        log_file.write("{:.2f} - {}: Arrive ballast at {} (Distance: {} NM, Travel time: {:.2f} days) \n".format(env.now(),
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

    with open('logs/results.txt', 'a') as results_file:
        results_file.seek(0)
        results_file.truncate()

    results = []

    for no_cargoes in BFB_CARGOES:
        LOAD_PORTS = load_ports(no_cargoes)

        for no_vessels in NO_OF_VESSELS:

            for CRUISE_SPEED in CRUISE_SPEEDS:

                for MEAN_PORT_DISRUPT in MEAN_PORT_DISRUPT_VALUES:

                    log_filename = str(no_cargoes) + "cargoes-" + str(no_vessels) + "vessels-" + str(CRUISE_SPEED) + "knots-"+ str(MEAN_PORT_DISRUPT)+"avg_disrupt.txt"
                    with open ('logs/'+log_filename, 'a') as log_file:
                        log_file.seek(0)
                        log_file.truncate()

                        env = sim.Environment(time_unit="days")
                        env.time_to_str_format('{:10.2f}')

                        vessels = [Vessel(name=name) for name in VESSELS[:no_vessels]]

                        for load_port, parameters in LOAD_PORTS.items():
                            cargogenerators[load_port] = CargoGenerator(load_port=load_port, parameters=parameters)

                        cargo_queue = sim.Queue("cargo_queue")

                        env.run(till=SIM_DURATION)

                        log_file.write("\n==================================================================================\n\n")
                        log_file.write(cargo_queue.print_statistics(as_str=True))
                        log_file.write("\n")
                        log_file.write(cargo_queue.print_histograms(as_str=True))
                        log_file.write("\n")
                        log_file.write(cargo_queue.print_info(as_str=True))

                        for vessel in vessels:
                            log_file.write("\n")
                            log_file.write(vessel.status.print_histogram(values=True, as_str=True))
                            log_file.write("\n")

                        with open ('logs/results.txt', 'a') as results_file:
                            results_file.write("Cargoes: {}, Vessels: {}, Speed: {} knots, Mean Disruption: {} hours\n \n".format(no_cargoes, no_vessels, CRUISE_SPEED, MEAN_PORT_DISRUPT))
                            results_file.write("Maximum length of stay in queue: {:.2f}\n".format(cargo_queue.length_of_stay.maximum()))
                            results_file.write("Maximum length of stay in queue, adjusted: {:.2f}\n".format(cargo_queue.length_of_stay.maximum()+1.8))
                            results_file.write("Average idle time over vessels: {:.2%}\n \n".format(average_passive_time(vessels)))
                            results_file.write("\n")
                            results_file.write(cargo_queue.print_histograms(as_str=True, exclude=[cargo_queue.length]))
                            results_file.write("\n")
                            results_file.write("==================================================================\n")

                        results.append(",".join([str(no_cargoes), str(no_vessels), str(CRUISE_SPEED), str(MEAN_PORT_DISRUPT), "{:.1f}".format(cargo_queue.length_of_stay.maximum()), "{:.0%}".format(average_passive_time(vessels)), "{:.1f}".format(cargo_queue.length_of_stay.maximum()+1.8), "{:.0%}".format(average_passive_time(vessels))]))

    # f = open("logs/results.csv", "w")
    # f.seek(0)
    # f.truncate()
    # f.write("\n".join(results))
    # f.close()