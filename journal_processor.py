from queue import Queue
from threading import Thread
from time import sleep

from context import GameState, PluginContext
from modules import legacy
from modules.lib import thread
from modules.lib.journal import Coords, JournalEntry


# Будем использовать threading.Thread вместо кастомного modules.lib.thread.Thread,
# чтобы избежать остановки обработчика до того, как он закончит разбирать очередь.

class JournalProcessor(Thread):
    def __init__(self):
        super().__init__(name="Triumvirate journal entry processor")
        self.queue: Queue = PluginContext._event_queue
        self._startup = True
        self._stop = False


    def run(self):
        while not self._stop:
            if self.queue.empty():
                sleep(1)
                continue
            try:
                entry = self.queue.get(block=False)
                match entry["type"]:
                    case "journal_entry":
                        self.on_journal_entry(*entry["data"])
                    case "dashboard_entry":
                        self.on_dashboard_entry(*entry["data"])
                    case "cmdr_data":
                        self.on_cmdr_data(*entry["data"])
                    case "plugin_stop":
                        self.on_plugin_stop()
                    case _:
                        raise ValueError("unknown entry type")
            except Exception as e:
                PluginContext.logger.error("Uncatched exception while processing a journal entry.\n%s", str(entry), exc_info=e)
                # TODO: отправка логов
                # TODO: убрать после тестирования 1.12.0
                PluginContext.notifier.send(
                    (
                        "Неожиданная ошибка при обработке логов! "
                        "Дальнейшая корректная работа плагина не гарантирована - перезапустите EDMC. "
                        "Пожалуйста, сообщите @elcy."
                    ),
                    timeout=0
                )


    def on_journal_entry(self, cmdr: str | None, is_beta: bool, system: str | None, station: str | None, entry: dict, state: dict):
        GameState.game_in_beta = is_beta
        GameState.station = station
        GameState.odyssey = state["Odyssey"]

        # ПРОВЕРКА КОМАНДИРА
        new_cmdr = GameState.cmdr
        if entry["event"] == "Commander":
            new_cmdr = entry["Name"]
        elif entry["event"] == "LoadGame":
            new_cmdr = entry["Commander"]
        elif GameState.cmdr is None and cmdr:   # доверимся данным EDMC
            new_cmdr = cmdr

        if new_cmdr != GameState.cmdr:
            GameState.cmdr = new_cmdr
            PluginContext.logger.debug(f"New CMDR: {GameState.cmdr}. Fetching the squadron.")
            GameState.squadron, GameState.legacy_sqid = legacy.fetch_squadron()
            PluginContext.logger.debug(f"Squadron set to {GameState.squadron}, SQID set to {GameState.legacy_sqid}.")

        # РЕПОРТ ВЕРСИИ ПЛАГИНА ПРИ ЗАПУСКЕ
        if self._startup and GameState.cmdr is not None:
            PluginContext.logger.debug("Reporting the plugin version.")
            legacy.report_version()
            self._startup = False

        # ПРОВЕРКА ЛОКАЦИИ
        # Комплексная тема, тут может быть несколько сценариев.
        # 1) Обычный вход в игру или прыжок
        if entry["event"] in ("Location", "FSDJump", "CarrierJump"):
            PluginContext.systems_module.cache_system(entry)
            GameState.system = entry["StarSystem"]
            GameState.system_address = entry["SystemAddress"]
            GameState.system_coords = Coords(*entry["StarPos"])
            GameState.pending_jump_system = None
            GameState.pending_jump_system_id = None
            PluginContext.logger.debug(
                f"{entry['event']} detected. Location change: "
                f"system {GameState.system} (id {GameState.system_address}), coords {GameState.system_coords}."
            )
            PluginContext.systems_module.hide_coords_warning()

        # 2) Игрок запустил плагин после входа в игру, и у нас ничего нет. Придётся полагаться на данные EDMC
        elif entry["event"] == "StartUp":
            PluginContext.logger.debug("Seems like the game is already running. Using EDMC's location data.")
            GameState.system = state.get("SystemName")
            GameState.system_address = state.get("SystemAddress")
            GameState.system_coords = Coords(*state["StarPos"]) if "StarPos" in state else None
            if GameState.system_coords is None:
                PluginContext.logger.debug("EDMC didn't provide us with the coordinates, showing user warning.")
                PluginContext.systems_module.show_coords_warning()
            PluginContext.logger.debug(
                f"Location change: system {GameState.system} (id {GameState.system_address}), coords {GameState.system_coords}."
            )

        # 3) Готовящийся прыжок - мы всё ещё в старой системе
        elif entry["event"] == "StartJump" and entry["JumpType"] == "Hyperspace":
            GameState.pending_jump_system = entry.get("StarSystem")
            GameState.pending_jump_system_id = entry.get("SystemAddress")
            PluginContext.logger.debug(
                f"Jump initiated, pending system set to {GameState.pending_jump_system} (id {entry['SystemAddress']})."
            )

        # 4) Прыжок совершён, но FSD/CarrierJump ещё не было, а данные из новой системы уже пошли (обычно это FSSSignalDiscovered)
        elif (
            "SystemAddress" in entry
            and entry["SystemAddress"] != GameState.system_address
            and entry["event"] not in ("NavRoute", "FSDTarget", "CarrierBuy", "CarrierJumpRequest", "CarrierLocation")
        ):
            PluginContext.logger.debug("Detected SystemAddress mismatch.")
            if (system_id := entry["SystemAddress"]) == GameState.pending_jump_system_id:
                GameState.system = GameState.pending_jump_system
                GameState.system_address = GameState.pending_jump_system_id
                GameState.system_coords = PluginContext.systems_module.get_system_coords(GameState.system_address)
                PluginContext.logger.debug(
                    f"New id ({system_id}) corresponds with the pending jump. Current system set to {GameState.system}, "
                    f"coords = {GameState.system_coords}."
                )
                # pending-и сохраним до ивента прыжка, там сбросим
            else:
                # прыгнули не пойми куда??
                PluginContext.logger.warning(
                    f"Unexpected misjump: new system id ({system_id}) doesn't match the pending one "
                    f"({GameState.pending_jump_system_id}). Attempting to fetch the system name and coords..."
                )
                new_system = PluginContext.systems_module.get_system_name(system_id)
                new_coords = PluginContext.systems_module.get_system_coords(system_id)
                if None not in (new_system, new_coords):
                    GameState.system = new_system
                    GameState.system_address = system_id
                    GameState.system_coords = new_coords
                    PluginContext.logger.warning(f"System changed to {new_system}, coords: {new_coords}.")
                else:
                    # в кэше данных не нашлось, вытянуть с интернетов тоже не вышло
                    PluginContext.logger.warning("No info on the new system id found. Keeping the old system for now.")
            if GameState.system_coords is None:
                PluginContext.logger.debug("System coordinates unknown, showing user warning.")
                PluginContext.systems_module.show_coords_warning()

        # ПЕРЕДАЧА ДАННЫХ МОДУЛЯМ
        # Как видно, после перехода на GameState - JournalEntry как таковой стал не нужен.
        # TODO: отказ от него будет долгим и болезненным, но надо.
        journal_entry = JournalEntry(
            cmdr=GameState.cmdr,
            is_beta=GameState.game_in_beta,
            system=GameState.system,
            systemAddress=GameState.system_address,
            station=GameState.station,
            data=entry,
            state=state,
            coords=GameState.system_coords
        )

        if entry["event"] in ('SendText', 'RecieveText'):
            for mod in PluginContext.active_modules:
                try:
                    mod.on_chat_message(journal_entry)
                except Exception as e:
                    PluginContext.logger.error(f"Exception in module {mod} while processing a chat message.", exc_info=e)
                    # TODO: убрать после тестирования 1.12.0
                    PluginContext.notifier.send("Ошибка при обработке логов. Пожалуйста, сообщите @elcy.", 0)
        else:
            for mod in PluginContext.active_modules:
                try:
                    mod.on_journal_entry(journal_entry)
                except Exception as e:
                    PluginContext.logger.error(f"Exception in module {mod} while processing a journal entry.", exc_info=e)


    def on_dashboard_entry(self, cmdr: str | None, is_beta: bool, entry: dict):
        GameState.game_in_beta = is_beta

        GameState.pips = entry.get("Pips")
        GameState.firegroup = entry.get("Firegroup")
        GameState.gui_focus = entry.get("GuiFocus")
        GameState.fuel_main = entry.get("Fuel", dict()).get("FuelMain")
        GameState.fuel_reservoir = entry.get("Fuel", dict()).get("FuelReservoir")
        GameState.cargo = entry.get("Cargo")
        GameState.legal_state = entry.get("LegalState")
        GameState.latitude = entry.get("Latitude")
        GameState.longitude = entry.get("Longitude")
        GameState.altitude = entry.get("Altitude")
        GameState.heading = entry.get("Heading")
        GameState.body_name = entry.get("BodyName")
        GameState.planet_radius = entry.get("PlanetRadius")
        GameState.balance = entry.get("Balance")
        GameState.destination = entry.get("Destination")
        GameState.oxygen = entry.get("Oxygen")
        GameState.health = entry.get("Health")
        GameState.selected_weapon = entry.get("SelectedWeapon")
        GameState.temperature = entry.get("Temperature")
        GameState.gravity = entry.get("Gravity")

        if (flags := entry.get("Flags")) is not None:
            GameState.flags.update(flags)
        if (flags2 := entry.get("Flags2")) is not None:
            GameState.flags2.update(flags2)


    def on_cmdr_data(self, data: dict, is_beta: bool):
        GameState.game_in_beta = is_beta
        for mod in PluginContext.active_modules:
            mod.on_cmdr_data(data, is_beta)


    def on_plugin_stop(self):
        PluginContext.logger.info("Stopping the plugin.")
        for mod in PluginContext.active_modules:
            try:
                mod.on_close()
            except Exception as e:
                PluginContext.logger.error(f"Exception in module {mod} on shutdown.", exc_info=e)
        PluginContext.systems_module.on_close()
        thread.Thread.stop_all()
        self._stop = True
