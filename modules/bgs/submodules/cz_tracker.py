import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from context import PluginContext, GameState # noqa
from legacy import URL_GOOGLE

from modules.bgs.submodule_base import Submodule


MINIMUM_SPACE_KILLS = 5
MINIMUM_ONFOOT_KILLS = 20


@dataclass
class Conflict:
    cmdr: str
    conflict_type: Literal['Space', 'OnFoot']
    system: str
    intensity: Literal['Low', 'Medium', 'High'] = None
    kills: int = 0
    bonds: int = 0
    timestamp_started: datetime = None
    timestamp_finished: datetime = None
    ally_faction: str = None
    enemy_faction: str = None
    settlement: str = None


class ConflictInfoFrame(tk.Frame):
    ...


class CZTracker(Submodule):
    def __init__(self):
        self.conflict: Conflict = None
        self.gamemode: Literal['Open', 'Group', 'Solo'] = 'Open'    # если наверняка не знаем, будем предполагать небезопасный вариант


    def on_journal_entry(self, entry: dict):
        event = entry["event"]
        match event:
            case "LoadGame": self.gamemode = entry["GameMode"]
            case "SupercruiseDestinationDrop": self.on_supercruise_drop(entry)
            case "ApproachSettlement": self.on_settlement_approached(entry)
            case "DropshipDeploy": self.on_dropship_deploy(entry)
            case "FactionKillBond": self.on_kill(entry)
            case "StartJump": self.end_conflict(entry)
            case "BookDropship" | "BookTaxi": self.on_book_dropship(entry)
            case "Music": self.on_music_event(entry)
            case "Shutdown" | "Died" | "SelfDestruct": self.end_conflict(entry, early=True)


    def on_supercruise_drop(self, entry: dict):
        signal: str = entry["Type"]
        if "$Warzone_PointRace" not in signal:
            return
        # "$Warzone_PointRace_High:#index=1;"
        intensity = signal.removeprefix("$Warzone_PointRace_").split(":")[0]
        if intensity == "Med":
            intensity = "Medium"
        self.conflict = Conflict(
            cmdr=GameState.cmdr,
            conflict_type='Space',
            system=GameState.system,
            intensity=intensity,
            timestamp_started=datetime.fromisoformat(entry["timestamp"])
        )


    def on_settlement_approached(self, entry: dict):
        if self.confict is not None:
            return
        self.confict = Conflict(
            cmdr=GameState.cmdr,
            conflict_type='OnFoot',
            system=GameState.system,
            settlement=entry["Name"]
        )


    def on_dropship_deploy(self, entry: dict):
        if self.confict is None:
            return
        if self.confict.timestamp_started is None:
            self.confict.timestamp_started = datetime.fromisoformat(entry["timestamp"])


    def on_kill(self, entry: dict):
        if self.confict is None:
            return
        self.confict.ally_faction = entry["AwardingFaction"]
        self.confict.enemy_faction = entry["VictimFaction"]
        self.confict.bonds += entry["Reward"]
        self.confict.kills += 1


    def on_book_dropship(self, entry: dict):
        if self.confict is None:
            return
        if entry["Retreat"] is True:
            self.end_conflict()


    def on_music_event(self, entry: dict):
        if self.confict is None or entry["MusicTrack"] != "MainMenu":
            return
        # в космических это досрочный выход
        # в пеших - возможный релог после завершения
        self.end_conflict(early=(self.confict.conflict_type == "Space"))


    def end_conflict(self, entry: dict, early: bool = False):
        if self.confict is None:
            return
        if early:
            self.confict = None
            return
        self.confict.timestamp_finished = datetime.fromisoformat(entry["timestamp"])

        if (
            self.confict.conflict_type == 'Space' and self.confict.kills < MINIMUM_SPACE_KILLS
            or self.confict.conflict_type == 'OnFoot' and self.confict.kills < MINIMUM_ONFOOT_KILLS
        ):
            # недостаточно убийств - досрочный выход
            self.confict = None
            return

        if self.gamemode == 'Open':
            # TODO: подтверждение у юзера
            pass
        else:
            self._send_confict_info(self.confict)
        self.confict = None


    @classmethod
    def _send_confict_info(cls, confict: Conflict):
        match confict.intensity:
            case "Low":     weight = 0.25
            case "Medium":  weight = 0.5
            case "High":    weight = 1
            case _:         weight = 0.25
        url = f'{URL_GOOGLE}/1FAIpQLSepTjgu1U8NZXskFbtdCPLuAomLqmkMAYCqk1x0JQG9Btgb9A/formResponse'
        params = {
            "entry.1673815657": confict.timestamp_started,
            "entry.1896400912": confict.timestamp_finished,
            "entry.1178049789": confict.cmdr,
            "entry.721869491": confict.system,
            "entry.1671504189": confict.conflict_type,
            "entry.461250117": confict.settlement,
            "entry.428944810": confict.intensity,
            "entry.1396326275": str(weight).replace('.', ','),
            "entry.1674382418": confict.ally_faction,
            "entry.1383403456": confict.ally_faction,
            "usp": "pp_url"
        }
        cls.core.send_data(url, params, [confict.system])
