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