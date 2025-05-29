import requests
import sqlite3
from queue import Queue
from threading import Lock
from typing import Any, Callable

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
    REFRESH_TIME = 30 * 60  # s
    FETCH_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTDY_aCGkppsZVZI_XhjBo_E3dxvGWilsOjpti9bPpqFLHM7Ar47pHfTeeSUfjLW3lI3hzsfy0YVCl7/pub?gid=1163755226&single=true&output=csv"  # noqa: E501

    def __init__(self, callback: Callable[[list[str]], Any]):
        self._callback = callback
        super().__init__(name="Triumvirate.BGSFilterUpdater")

    def do_run(self):
        while True:
            self.fetch()
            self.sleep(self.REFRESH_TIME)

    def fetch(self):
        PluginContext.logger.debug("Starting BGS systems data updating process...")
        try:
            resp = requests.get(self.FETCH_URL)
            resp.raise_for_status()
        except requests.RequestException as e:
            PluginContext.logger.error("Couldn't fetch the systems list. Exception info:", exc_info=e)
            return
        systems = resp.text.splitlines()
        if len(systems) == 0:
            PluginContext.logger.error("The systems list was empty, skipping the update.")
            return
        self._callback(systems)


class Filter:
    def __init__(self):
        self.__threadlock = Lock()
        self.updater = FilterUpdater(self._on_data_update)
        self.updater.start()
        self.bgs_reports_queue = Queue()
        self._tracked_systems: set[str] = set()

    def dispatch_bgs_report(
        self,
        url: str,
        params: dict,
        affected_systems: list[str],
    ):
        if not self._data:
            PluginContext.logger.debug(
                "BGS report check cannot be done: no tracked systems data yet. Saving the report for a delayed check."
            )
            self.bgs_reports_queue.put((affected_systems, url, params))
            return
        with self.__threadlock:
            if not any(s in self._tracked_systems for s in affected_systems):
                PluginContext.logger.debug("None of the provided affected systems are tracked, ignoring this BGS report.")
                return
            PluginContext.logger.debug("Sending a BGS report.")
            GoogleReporter(url, params).start()

    def _on_data_update(self, systems: list[str]):
        with self.__threadlock:
            self._tracked_systems = set(systems)
        if not self.bgs_reports_queue.empty():
            PluginContext.logger.debug("Processing delayed BGS report checks:")
            while not self.bgs_reports_queue.empty():
                self.dispatch_bgs_report(*self.bgs_reports_queue.get())


class BGSCore(Module):
    localized_name = _translate("BGS module")
    DB_PATH = PluginContext.plugin_dir / "userdata" / "BGSdata.db"

    def __init__(self):
        self.filter = Filter()
        self.database = sqlite3.connect(self.DB_PATH, check_same_thread=False)
        submodule_base.init_submodules(self)
        self.submodules = submodule_base.get_submodules()
        if self.submodules:
            PluginContext.logger.info(
                f"{len(self.submodules)} submodules initiated: " + ', '.join(s.__class__.__qualname__ for s in self.submodules)
            )
        else:
            PluginContext.logger.error("No submodules found. Disabling the BGS module.")
            self.enabled = False
            PluginContext.notifier.send(_translate("BGS module encountered an error during initialization and was disabled."), 0)

    def on_close(self):
        for mod in self.submodules:
            mod.on_close()
        self.database.close()

    def on_journal_entry(self, entry: JournalEntry):
        for subm in self.submodules:
            try:
                subm.on_journal_entry(entry.data)
            except Exception as e:
                PluginContext.logger.error(
                    f"Exception in BGS submodule {subm} while processing a journal entry:",
                    exc_info=e
                )

    def send_data(self, url: str, params: dict, affected_systems: list[str]):
        """
        Небольшая прослойка для субмодулей, чтобы им не обращаться напрямую к фильтру.
        """
        self.filter.dispatch_bgs_report(url, params, affected_systems)
