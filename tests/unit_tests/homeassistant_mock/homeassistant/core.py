class CoreState:
    running = "running"
    not_running = "not_running"


class HomeAssistant:
    def __init__(self):
        self.state = CoreState.running
        self.services = None
        self.data = {}
        self.bus = None
        self.config_entries = None
        self.states = None


class ServiceCall:
    def __init__(self, data=None):
        self.data = data or {}


EventStateChangedData = dict


def callback(func):
    return func
