import tkinter as tk
from tkinter import ttk

import myNotebook as nb  # type: ignore
from config import config as edmc_config  # type: ignore

from core.context import PluginContext
from core.debug import Debug
from core.journal_processor import JournalProcessor
from core.notifier import Notifier
from core.sound_player import Player
from core.systems import SystemsCache
from lib import thread
from lib.module import Module
from modules.bgs import BGS
from modules.canonn_api import CanonnRealtimeAPI
from modules.colonisation import DeliveryTracker
from modules.exploring.canonn_codex_poi import CanonnCodexPOI
from modules.exploring.visualizer import Visualizer
from modules.fc_tracker import FC_Tracker
from modules.patrol import PatrolModule
from modules.squadron import SquadronTracker


def init_version():
    Debug.setup(PluginContext.logger)
    PluginContext.sound_player = Player()

    # очистка устаревших ключей конфигурации
    edmc_config.delete("Triumvirate.Canonn:HideCodex", suppress=True)
    edmc_config.delete("Triumvirate.Canonn", suppress=True)
    # TODO: раскомментить после релиза 1.12.0
    # edmc_config.delete("Triumvirate.CanonnDebug", suppress=True)
    # edmc_config.delete("Triumvirate.DisableAutoUpdate", suppress=True)
    # edmc_config.delete("Triumvirate.RemoveBackup", suppress=True)
    # edmc_config.delete("Triumvirate.Updater.LocalVersion", supress=True)


def plugin_app(parent: tk.Misc) -> tk.Frame:
    """
    Updater вызывает эту функцию для получения UI плагина,
    который затем будет размещён в главном окне EDMC.
    """
    frame = tk.Frame(parent)
    frame.grid_columnconfigure(0, weight=1)
    PluginContext.notifier = Notifier(frame, 4)    # его надо инициализировать первым, но маппить в самый низ
    PluginContext.systems_cache = SystemsCache(frame, 0)
    PluginContext.exp_visualizer = Visualizer(frame, 1)
    PluginContext.patrol_module = PatrolModule(frame, 2)
    PluginContext.fc_tracker = FC_Tracker(frame, 3)
    PluginContext.bgs_module = BGS(frame, 4)

    # эти модули не имеют UI, но стартуем их здесь же
    PluginContext.canonn_api = CanonnRealtimeAPI()
    PluginContext.colonisation_tracker = DeliveryTracker()
    PluginContext.sq_tracker = SquadronTracker()
    PluginContext.canonn_codex_poi = CanonnCodexPOI()

    # TODO: on_start вообще не нужен с новой системой обновлений, отредактировать модули
    for mod in PluginContext.active_modules:
        mod.on_start(PluginContext.plugin_dir)

    # в последнюю очередь запускаем обработчик событий
    PluginContext.journal_processor = JournalProcessor()
    PluginContext.journal_processor.start()

    return frame


def plugin_prefs(parent: tk.Misc, cmdr: str | None, is_beta: bool) -> tk.Frame:
    """
    EDMC вызывает эту функцию для получения вкладки настроек плагина.
    """
    # TODO: перейти на pack

    def rowgen():
        row = 1     # Debug.plugin_prefs всегда занимает нулевой ряд
        while True:
            yield row
            row += 1
    rg = rowgen()

    frame = tk.Frame(parent, bg="white")
    frame.grid_columnconfigure(0, weight=1)
    Debug.plugin_prefs(frame)
    ttk.Separator(frame, orient="horizontal").grid(row=next(rg), column=0, pady=5, sticky="EW")

    for mod in PluginContext.active_modules:
        # некоторые модули не имеют настроек, а лишние линии нам не нужны
        if mod.__class__.draw_settings != Module.draw_settings:
            mod.draw_settings(frame, cmdr, is_beta, next(rg))
            ttk.Separator(frame, orient="horizontal").grid(row=next(rg), column=0, pady=5, sticky="EW")

    nb.Label(
        frame, text=PluginContext._tr_template("<SETTINGS_SUPPORT_MESSAGE>", filepath=__file__)
    ).grid(row=next(rg), column=0, sticky="NW")
    return frame


def prefs_changed(cmdr: str | None, is_beta: bool):
    """
    EDMC вызывает эту функцию при сохранении настроек пользователем.
    """
    Debug.prefs_changed()
    for mod in PluginContext.active_modules:
        mod.on_settings_changed(cmdr, is_beta)


def plugin_stop():
    """
    EDMC вызывает эту функцию при закрытии.
    """
    PluginContext.logger.info("Stopping the plugin.")
    PluginContext.journal_processor.set_stop()
    PluginContext.journal_processor.join()
    for mod in PluginContext.active_modules:
        mod.on_close()
    PluginContext.logger.debug("Joining threads...")
    thread.BasicThread.join_all()
    PluginContext.logger.debug("Done, exiting.")
