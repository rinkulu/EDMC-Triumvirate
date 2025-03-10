from queue import Queue
from threading import Lock

from context import PluginContext
from modules.legacy import GoogleReporter
from modules.lib.journal import JournalEntry
from modules.lib.module import Module
from modules.lib.thread import Thread

from . import submodule_base

# isort: off
import functools
_translate = functools.partial(PluginContext._tr_template, filepath=__file__)
# isort: on


class FilterUpdater(Thread):
    def __init__(self, filter_instance: 'Filter'):
        self._filter = filter_instance
        super().__init__(name="Triumvirate.BGSFilterUpdater")

    def do_run(self):
        pass


class Filter:
    _data: dict[str, dict[str, float]] = None       # {faction: {system: influence}}
    _additional_systems: list[str] = None

    def __init__(self):
        self.__threadlock = Lock()
        self.updater = FilterUpdater(self)
        self.delayed_checks = Queue()
        self.delayed_bgs = Queue()
        self.updater.start()

    @property
    def tracked_factions(self) -> list[str]:
        return list(self._data.keys())

    @property
    def tracked_systems(self) -> list[str]:
        from_factions = [system for faction_data in self._data.values() for system in faction_data.keys()]
        return list(set(from_factions + self._additional_systems))

    def get_faction_systems(self, faction: str) -> list[str] | None:
        if faction not in self.tracked_factions:
            return None
        return self._data[faction].keys()

    def remove_faction_system(self, faction: str, system: str):
        if faction not in self.tracked_factions:
            return
        del self._data[faction][system]

    def get_saved_influence(self, faction: str, system: str) -> float | None:
        return self._data.get(faction, {}).get(system)

    def set_saved_influence(self, faction: str, system: str, inf: float):
        if faction not in self.tracked_factions:
            return
        self._data[faction][system] = inf

    def check_local_factions(self, entry: dict):
        if not self._data:
            self.delayed_checks.put(entry)
            return
        with self.__threadlock:
            system: str = entry["StarSystem"]
            local_factions: dict[str, dict] = {f.get("Name"): f for f in entry.get("Factions", [])}
            if None in list(local_factions.keys()):
                PluginContext.logger.error(f"Empty faction name. Raw entry: {entry}")
                local_factions = {k: v for k, v in local_factions.items() if k is not None}

            local_tracked_factions = [f for f in local_factions if f in self.tracked_factions]
            for faction in local_tracked_factions:
                data = local_factions[faction]
                state = "Present"
                for item in data.get("ActiveStates", []):
                    if (f_state := item.get("State")) in ("Retreat", "Expansion"):
                        state = f_state
                saved_inf = self.get_saved_influence(faction, system)
                current_inf = data.get("Influence", 0.0)
                if saved_inf is None:
                    self.report_expansion(faction, system, current_inf, state)
                elif saved_inf != current_inf:
                    self.report_inf_change(faction, system, current_inf, state)
                self.set_saved_influence(faction, system, current_inf)

            for tracked_f in self.tracked_factions:
                if system in self.get_faction_systems(tracked_f) and tracked_f not in local_factions:
                    self.report_retreat(faction, system)
                    self.remove_faction_system(faction, system)

    def dispatch_bgs_report(
        self,
        affected_systems: list[str] | None,
        affected_factions: list[str] | None,
        url: str, params: dict
    ):
        if not affected_systems and not affected_factions:
            raise ValueError("At least one of 'affected_factions' or 'affected_systems' must be provided.")
        if not self._data:
            self.delayed_bgs.put((affected_systems, affected_factions, url, params))
            return
        with self.__threadlock:
            if affected_systems and not any(s in self.tracked_systems for s in affected_systems):
                return
            if affected_factions and not any(f in self.tracked_factions for f in affected_factions):
                return
            GoogleReporter(url, params).start()

    def report_expansion(self, faction: str, system: str, inf: float):
        pass

    def report_retreat(self, faction: str, system: str):
        pass

    def report_inf_change(self, faction: str, system: str, inf: float):
        pass

    def _on_tracked_update(self, data: dict[str, dict[str, float]], additional_systems: list[str]):
        with self.__threadlock:
            self._data = data
            self._additional_systems = additional_systems
        while not self.delayed_checks.empty():
            self.check_local_factions(self.delayed_checks.get())
        while not self.delayed_bgs.empty():
            self.dispatch_bgs_report(*self.delayed_bgs.get())


class BGSCore(Module):
    localized_name = _translate("BGS module")

    def __init__(self):
        self.filter = Filter()
        submodule_base.init_submodules(self)
        self.submodules = submodule_base.get_submodules()

    def on_journal_entry(self, entry: JournalEntry):
        if entry.data.get("event") in ("FSDJump", "Location"):
            self.filter.check_local_factions(entry.data)
        for subm in self.submodules:
            try:
                subm.on_journal_entry(entry.data)
            except Exception as e:
                PluginContext.logger.error(
                    f"Exception in BGS submodule {subm} while processing a journal entry:",
                    exc_info=e
                )
