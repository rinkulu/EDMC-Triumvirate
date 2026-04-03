import requests

import settings
from modules.debug import debug
from modules.lib.cache import Cache


class SystemsModule:
    def __init__(self):
        self.cache = Cache(max_size=1024, name="SYSTEMS_CACHE")
        self.cache.start()

    def add_system(self, entry: dict):
        system = entry["StarSystem"]
        coords = entry["StarPos"]
        self.cache[system] = coords

    def get_system_coords(self, system):
        try:
            return self.cache[system]
        except KeyError:
            coords = self.fetch_system(system)
            if coords is not None:
                self.cache[system] = coords
            return coords

    def fetch_system(self, system: str) -> tuple[float, float, float] | None:
        try:
            resp = requests.get(
                url=f"{settings.galaxy_url}/api/v1/lookup",
                params={"name": system},
                timeout=5,
            )
            resp.raise_for_status()
            json = resp.json() or dict()
            x, y, z = json.get("x"), json.get("y"), json.get("z")
            if None not in (x, y, z):
                debug(f"Got coordinates for {system} from CEC API: {x}, {y}, {z}")
                return x, y, z  # type: ignore
            else:
                debug(f"CEC API doesn't contain valid coordinates for {system}, attempting Spansh")
        except Exception as e:
            debug(f"Failed to retrieve coordinates from CEC API, attempting Spansh: {e}.")

        try:
            resp = requests.get(
                url="https://www.spansh.co.uk/api/search",
                params={"q": system},
                timeout=5,
            )
            resp.raise_for_status()
            record = next(
                (
                    s["record"] for s in resp.json()["results"]
                    if s["type"] == "system"
                    and s["record"]["name"] == system
                ),
                None
            )
            if record is None:
                debug(f"Spansh doesn't contain a record for {system}")
                return None
            else:
                x, y, z = record["x"], record["y"], record["z"]
                debug(f"Got coordinates for {system} from Spansh: {x}, {y}, {z}")
                return x, y, z
        except Exception as e:
            debug(f"Failed to retrieve coordinates from Spansh: {e}")
            return None
