import logging
import queue
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from semantic_version import Version
from tkinter import ttk

import myNotebook as nb  # type: ignore
from config import config as edmc_config  # type: ignore

from Triumvirate.core.context import PluginContext
from Triumvirate.lib import thread
from Triumvirate.lib.module import Module


def initialize(
    edmc_version: Version,
    plugin_name: str,
    plugin_version: Version,
    plugin_root_dir: Path,
    ui_parent: tk.Frame,
    logger: logging.Logger,
    event_queue: queue.Queue,
    translation_fn: Callable,
) -> tk.Frame:
    # 1) Заполнение начальных параметров
    PluginContext.plugin_name = plugin_name
    PluginContext.plugin_version = plugin_version
    PluginContext.user_agent = f"{plugin_name}.{plugin_version}"
    PluginContext.edmc_version = edmc_version
    PluginContext.plugin_dir = plugin_root_dir
    PluginContext.logger = logger
    PluginContext._tr_template = translation_fn

    # 2) Создание объектов ядра
    from Triumvirate.core.journal_processor import JournalProcessor
    from Triumvirate.core.notifier import Notifier
    from Triumvirate.core.sound_player import Player
    from Triumvirate.core.systems import SystemsCache
    frame = tk.Frame(ui_parent)
    PluginContext.journal_processor = JournalProcessor(event_queue)
    PluginContext.sound_player = Player()
    PluginContext.notifier = Notifier(frame, 5)  # его надо инициализировать первым, но маппить в самый низ
    PluginContext.systems_cache = SystemsCache(frame, 0)

    # 3) Создание модулей
    from Triumvirate.modules.bgs import BGS
    from Triumvirate.modules.canonn_api import CanonnRealtimeAPI
    from Triumvirate.modules.colonisation import DeliveryTracker
    from Triumvirate.modules.exploring.canonn_codex_poi import CanonnCodexPOI
    from Triumvirate.modules.exploring.visualizer import Visualizer
    from Triumvirate.modules.fc_tracker import FC_Tracker
    from Triumvirate.modules.patrol import PatrolModule
    from Triumvirate.modules.squadron import SquadronTracker
    PluginContext.exp_visualizer = Visualizer(frame, 1)
    PluginContext.patrol_module = PatrolModule(frame, 2)
    PluginContext.fc_tracker = FC_Tracker(frame, 3)
    PluginContext.bgs_module = BGS(frame, 4)
    PluginContext.canonn_api = CanonnRealtimeAPI()
    PluginContext.colonisation_tracker = DeliveryTracker()
    PluginContext.sq_tracker = SquadronTracker()
    PluginContext.canonn_codex_poi = CanonnCodexPOI()

    # 4) Запуск обработки событий
    clear_old_config_keys()
    PluginContext.journal_processor.start()

    return frame


def clear_old_config_keys():
    edmc_config.delete("Triumvirate.Canonn:HideCodex", suppress=True)
    edmc_config.delete("Triumvirate.Canonn", suppress=True)
    # TODO: раскомментить после релиза 1.12.0
    # edmc_config.delete("Triumvirate.CanonnDebug", suppress=True)
    # edmc_config.delete("Triumvirate.DisableAutoUpdate", suppress=True)
    # edmc_config.delete("Triumvirate.RemoveBackup", suppress=True)
    # edmc_config.delete("Triumvirate.Updater.LocalVersion", supress=True)
    # edmc_config.delete("Triumvirate.EnableDebugging", supress=True)


def plugin_prefs(parent: tk.Misc, cmdr: str | None, is_beta: bool) -> tk.Frame:
    """
    EDMC вызывает эту функцию для получения вкладки настроек плагина.
    """
    # TODO: перейти на pack

    def rowgen():
        row = 0
        while True:
            yield row
            row += 1
    rg = rowgen()

    frame = tk.Frame(parent, bg="white")
    frame.grid_columnconfigure(0, weight=1)
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
