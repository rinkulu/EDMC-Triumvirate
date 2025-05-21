class Coords:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __str__(self):
        return '[' + ', '.join(map(str, self)) + ']'


class JournalEntry:
    def __init__(
        self,
        cmdr: str,
        is_beta: bool,
        system: str,
        systemAddress: int,
        station: str,
        data: dict,
        state: dict,
        coords: Coords
    ):
        self.cmdr = cmdr
        self.is_beta = is_beta
        self.system = system
        self.systemAddress = systemAddress
        self.station = station
        self.data = data
        self.state = state
        self.coords = coords

    def as_dict(self):
        return {
            "cmdr": self.cmdr,
            "is_beta": self.is_beta,
            "system": self.system,
            "systemAddress": self.systemAddress,
            "station": self.station,
            "data": self.data,
            "state": self.state,
            "coords": {
                "x": self.coords.x,
                "y": self.coords.y,
                "z": self.coords.z,
            },
        }
