from context import GameState, PluginContext
from modules.bgs.submodule_base import Submodule
from modules.legacy import URL_GOOGLE


class ExpDataTracker(Submodule):
    def __init__(self):
        self.station_owner: str = None

    def on_journal_entry(self, entry: dict):
        event = entry["event"]
        if event == "Docked" or (event == "Location" and entry["Docked"] is True):
            self.station_owner = entry["StationFaction"]["Name"]
            return
        elif event == "Undocked" or (event == "Location" and entry["Docked"] is False):
            self.station_owner = None
            return
        elif event != "SellExplorationData":
            return

        # игнорируем флитаки
        if self.station_owner == "FleetCarrier":
            return

        url = f'{URL_GOOGLE}/1FAIpQLSenjHASj0A0ransbhwVD0WACeedXOruF1C4ffJa_t5X9KhswQ/formResponse'
        amount = entry["TotalEarnings"]
        params = {
            "entry.503143076": GameState.cmdr,
            "entry.1108939645": "SellExpData",
            "entry.127349896": GameState.system,
            "entry.442800983": GameState.station,
            "entry.48514656": self.station_owner,
            "entry.351553038": amount,
            "usp": "pp_url"
        }
        PluginContext.logger.debug(f"Sold exploration data: station owner - {self.station_owner}, total amount - {amount}cr.")
        self.core.send_data(url, params, [GameState.system])
