import csv
import requests
from dataclasses import dataclass, fields
from queue import Queue
from threading import Lock
from typing import Any, Callable, Literal

from context import GameState, PluginContext
from modules.bgs.submodule_base import Submodule
from modules.legacy import GoogleReporter
from modules.lib.thread import Thread

FactionState = Literal['Present', 'Pending retreat', 'Retreated', 'Conflict']
ConflictType = Literal['War', 'Election']
ConflictStatus = Literal['active', 'pending', 'finished']


@dataclass
class FactionSystemData:
    faction: str
    system: str
    influence: float = 0.0
    state: FactionState = "Present"
    conflict_type: ConflictType | None = None
    conflict_status: ConflictStatus | None = None
    conflict_enemy: str | None = None
    conflict_score: int | None = None
    conflict_score_enemy: int | None = None
    conflict_stake: str | None = None
    conflict_stake_enemy: str | None = None


class FactionDataFetcher(Thread):
    REFRESH_TIME = 30 * 60  # s
    REMOTE_DATA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTDY_aCGkppsZVZI_XhjBo_E3dxvGWilsOjpti9bPpqFLHM7Ar47pHfTeeSUfjLW3lI3hzsfy0YVCl7/pub?gid=1715591931&single=true&output=csv"  # noqa: E501

    def __init__(self, callback: Callable[[list[list[str]]], Any]):
        super().__init__()
        self._callback = callback

    def do_run(self):
        while True:
            self.fetch_data()
            self.sleep(self.REFRESH_TIME)

    def fetch_data(self):
        try:
            resp = requests.get(self.REMOTE_DATA_URL)
            resp.raise_for_status()
        except requests.RequestException as e:
            PluginContext.logger.error("Couldn't fetch factions data. Exception info:", exc_info=e)
            return
        reader = csv.reader(resp.text.splitlines())
        result = []
        for row in reader:
            # без активных конфликтов гугл порежет количество столбцов в csv
            if len(row) < len(fields(FactionSystemData)):
                row += [""] * (len(fields(FactionSystemData)) - len(row))
            result.append(row)
        if not result:
            return
        self._callback(result)


class FactionTracker(Submodule):
    """
    Следит за состоянием отслеживаемых фракций в их системах,
    сообщает при обнаружении изменений.
    """

    def __init__(self):
        self.data: dict[str, dict[str, FactionSystemData]] = dict()      # {faction: {system: FSD}}
        self.system_check_queue = Queue()
        self._threadlock = Lock()
        self._updater = FactionDataFetcher(self.on_data_update)
        self._updater.start()

    def on_journal_entry(self, entry: dict):
        if entry["event"] not in ("Location", "FSDJump"):
            return
        if not self.data:
            PluginContext.logger.debug(
                "Local factions checks cannot be done: no factions data yet. Saving the report for a delayed check."
            )
            self.system_check_queue.put(entry)
            return
        self.check_system_factions(entry)

    def check_system_factions(self, entry: dict):
        with self._threadlock:
            system: str = entry["StarSystem"]
            system_factions: dict[str, dict] = {f.get("Name"): f for f in entry.get("Factions", [])}
            if None in list(system_factions.keys()):
                PluginContext.logger.error(f"Empty faction name. Raw entry: {entry}")
                system_factions = {k: v for k, v in system_factions.items() if k is not None}

            tracked_system_factions = [f for f in system_factions if f in self.data]
            if tracked_system_factions:
                PluginContext.logger.debug("Tracked factions in the system: " + ', '.join(tracked_system_factions))
            tracked_factions_objects: list[FactionSystemData] = []

            for faction in tracked_system_factions:
                data = system_factions[faction]
                influence = data.get("Influence")
                if influence is None:
                    PluginContext.logger.error(f"Empty faction influence, skipping. Raw entry: {entry}.")
                    continue
                state = "Present"
                for active_state in (s.get("State") for s in data.get("ActiveStates", [])):
                    if active_state == "Retreat":
                        state = "Pending retreat"
                    elif active_state in ("War", "CivilWar", "Election"):
                        state = "Conflict"
                tracked_factions_objects.append(FactionSystemData(faction, system, influence, state))

            for faction in [name for name, systems in self.data.items() if system in systems]:
                if faction not in [f.faction for f in tracked_factions_objects]:
                    PluginContext.logger.debug(f"Detected retread of tracked faction '{faction}'. Reporting.")
                    self.report_faction_data_change(FactionSystemData(faction, system, 0, "Retreated"))
                    del self.data[faction][system]

            for system_conflict in entry.get("Conflicts", []):
                if (status := system_conflict["Status"]) == "":
                    status = "finished"
                match conflict_type := system_conflict["WarType"]:
                    case "war" | "civilwar": conflict_type = "War"
                    case "election": conflict_type = "Election"
                    case _:
                        PluginContext.logger.warning(f"Unknown conflict type: {conflict_type}. Raw entry: {entry}")
                        continue
                participants = [system_conflict["Faction1"], system_conflict["Faction2"]]
                for index, participant in enumerate(participants):
                    faction = participant
                    enemy = participants[index - 1]
                    for faction_obj in tracked_factions_objects:
                        if faction_obj.faction == faction["Name"]:
                            faction_obj.conflict_type = conflict_type
                            faction_obj.conflict_status = status
                            faction_obj.conflict_enemy = enemy["Name"]
                            faction_obj.conflict_score = faction["WonDays"]
                            faction_obj.conflict_score_enemy = enemy["WonDays"]
                            faction_obj.conflict_stake = faction["Stake"]
                            faction_obj.conflict_stake_enemy = enemy["Stake"]
                            break

            for new_data in tracked_factions_objects:
                faction = new_data.faction
                old_data = self.data[faction].get(system)
                if old_data == new_data:
                    PluginContext.logger.debug(f"No data updates for tracked faction '{faction}'.")
                    continue
                if old_data is None:
                    PluginContext.logger.debug(f"Detected expansion of tracked faction '{faction}'.")
                    # так делать низзя, но этот субмодуль будет исключением
                    self.core.filter._tracked_systems.add(system)
                    PluginContext.logger.debug(f"System '{system}' was added to the BGS Filter list of tracked systems.")
                elif new_data != self.data[faction][system]:
                    PluginContext.logger.debug(f"Detected a data update for tracked faction '{faction}':")
                    for field in fields(FactionSystemData):
                        if (old_value := getattr(old_data, field.name)) != (new_value := getattr(new_data, field.name)):
                            PluginContext.logger.debug(f"{field.name}: {old_value} -> {new_value}")
                self.data[faction][system] = new_data
                self.report_faction_data_change(new_data)

    def report_faction_data_change(self, new_data: FactionSystemData):
        url = "https://docs.google.com/forms/d/e/1FAIpQLSe04qEfF-Pj8bOcsYktryMQNaoO9ft0orOhSb3E6M_Jw2R_qQ/formResponse?usp=pp_url"
        params = {
            "entry.1705592545": GameState.cmdr,
            "entry.132634971": new_data.faction,
            "entry.719121673": new_data.system,
            "entry.880286539": new_data.influence,
            "entry.1723245318": new_data.state,
            "entry.1373861537": new_data.conflict_type,
            "entry.597895648": new_data.conflict_enemy,
            "entry.1216403281": new_data.conflict_status,
            "entry.807900121": new_data.conflict_score,
            "entry.2098736877": new_data.conflict_score_enemy,
            "entry.2070019885": new_data.conflict_stake,
            "entry.1471364504": new_data.conflict_stake_enemy
        }
        GoogleReporter(url, params).start()

    def on_data_update(self, new_data: list[list[str]]):
        def clean_row(row: list[str]):
            row = [None if item == "" else item for item in row]
            row[2] = float(row[2])                      # influence
            row[4] = row[4] or None                     # conflict_type
            row[5] = row[5] or None                     # conflict_status
            row[6] = row[6] or None                     # conflict_enemy
            row[7] = int(row[7]) if row[7] else None    # conflict_score
            row[8] = int(row[8]) if row[8] else None    # conflict_score_enemy
            row[9] = row[9] or None                     # conflict_stake
            row[10] = row[10] or None                   # conflict_stake_enemy
            return row

        with self._threadlock:
            PluginContext.logger.debug("Received updated factions data.")
            self.data.clear()
            for row in new_data:
                cleaned_row = clean_row(row)
                fsd = FactionSystemData(*cleaned_row)
                self.data.setdefault(fsd.faction, {})[fsd.system] = fsd
        if not self.system_check_queue.empty():
            PluginContext.logger.debug("Processing delayed system checks:")
            while not self.system_check_queue.empty():
                self.check_system_factions(self.system_check_queue.get())
