from context import GameState, PluginContext
from modules.bgs.submodule_base import Submodule
from modules.legacy import URL_GOOGLE


class VoucherTracker(Submodule):
    def __init__(self):
        self.station_owner: str = None
        self.redeemed_factions: list[str] = None

    def on_journal_entry(self, entry: dict):
        event = entry["event"]
        if event == "Docked" or (event == "Location" and entry["Docked"] is True):
            self.station_owner = entry["StationFaction"]["Name"]
            self.redeemed_factions = list()
            return
        elif event == "Undocked" or (event == "Location" and entry["Docked"] is False):
            self.station_owner = None
            self.redeemed_factions = None
            return
        elif event != "RedeemVoucher":
            return

        # игнорируем флитаки и юристов
        if self.station_owner == "FleetCarrier" or "BrokerPercentage" in entry:
            return

        url = f'{URL_GOOGLE}/1FAIpQLSenjHASj0A0ransbhwVD0WACeedXOruF1C4ffJa_t5X9KhswQ/formResponse'
        voucher_type = entry["Type"]
        cmdr = GameState.cmdr
        system = GameState.system

        if voucher_type == "CombatBond":
            faction_name = entry["Faction"]
            amount = entry["Amount"]
            PluginContext.logger.debug(f"Redeeming combat bonds: faction {faction_name}, amount: {amount}cr.")
            params = {
                "entry.503143076": cmdr,
                "entry.1108939645": voucher_type,
                "entry.127349896": system,
                "entry.442800983": "",
                "entry.48514656": faction_name,
                "entry.351553038": amount,
                "usp": "pp_url",
            }
            self.core.send_data(url, params, [system])

        elif voucher_type == "bounty":
            PluginContext.logger.debug("Redeeming bounties:")
            for faction in entry["Factions"]:
                faction_name = faction["Faction"]
                amount = faction["Amount"]
                if faction_name != "" and faction_name not in self.redeemed_factions:
                    PluginContext.logger.debug(f"Faction {faction_name}, amount: {amount}cr.")
                    params = {
                        "entry.503143076": cmdr,
                        "entry.1108939645": voucher_type,
                        "entry.127349896": system,
                        "entry.442800983": "",
                        "entry.48514656": faction_name,
                        "entry.351553038": amount,
                        "usp": "pp_url",
                    }
                    self.redeemed_factions.append(faction_name)
                    self.core.send_data(url, params, [system])
