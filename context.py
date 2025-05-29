from dataclasses import dataclass
from enum import Enum
from semantic_version import Version
from typing import TYPE_CHECKING, Protocol

# АХТУНГ: ничто из того, что здесь импортируется, не должно использовать начальные параметры контекста!
# См. load.py -> Updater.__use_local_version
import settings
from modules.lib.module import get_active_modules


if TYPE_CHECKING:
    # им можно, они тут для аннотаций типов и в рантайме не импортируются
    import logging
    from pathlib import Path
    from queue import Queue

    from journal_processor import JournalProcessor
    from modules.bgs import BGS
    from modules.canonn_api import CanonnRealtimeAPI
    from modules.colonisation import DeliveryTracker
    from modules.exploring.canonn_codex_poi import CanonnCodexPOI
    from modules.exploring.visualizer import Visualizer
    from modules.fc_tracker import FC_Tracker
    from modules.lib.journal import Coords
    from modules.lib.module import Module
    from modules.notifier import Notifier
    from modules.patrol import PatrolModule
    from modules.sound_player import Player
    from modules.squadron import Squadron_Tracker
    from modules.systems import SystemsModule


class TranslateFunc(Protocol):
    def __call__(self, x: str, filepath: str, lang: str = None) -> str:
        """
        :param x: Ключ перевода
        :param filepath: Путь к файлу (__file__), в котором вызывается функция
        :param optional lang: Позволяет явно указать, для какого языка будет взят перевод
        """
        ...


class _ClassProperty:
    """
    Заменяет связку @classmethod и @property (depricated в Python 3.11).
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func(owner)


@dataclass
class PluginContext:
    """
    Хранит параметры плагина и ссылки на его компоненты.
    """
    # параметры
    plugin_name: str                = "EDMC-Triumvirate"
    plugin_version: Version         = Version(settings.version)
    client_version: str             = f"{plugin_name}.{plugin_version}"
    edmc_version: Version           = None
    plugin_dir: 'Path'              = None

    # объекты
    logger: 'logging.Logger'        = None
    _event_queue: 'Queue'           = None
    _tr_template: TranslateFunc     = None
    journal_processor: 'JournalProcessor'   = None
    notifier: 'Notifier'            = None
    sound_player: 'Player'          = None

    # модули
    bgs_module: 'BGS'               = None
    canonn_api: 'CanonnRealtimeAPI' = None
    canonn_codex_poi: 'CanonnCodexPOI'  = None
    sq_tracker: 'Squadron_Tracker'  = None
    fc_tracker: 'FC_Tracker'        = None
    colonisation_tracker: 'DeliveryTracker' = None
    friendfoe                       = None      # TODO: оживить
    systems_module: 'SystemsModule' = None
    patrol_module: 'PatrolModule'   = None
    exp_visualizer: 'Visualizer'    = None

    @_ClassProperty
    def active_modules(cls) -> list['Module']:
        return get_active_modules()


# вспомогательные классы

class LegalState(str, Enum):
    CLEAN               = "Clean"
    ILLEGAL_CARGO       = "IllegalCargo"
    SPEEDING            = "Speeding"
    WANTED              = "Wanted"
    HOSTILE             = "Hostile"
    PASSENGER_WANTED    = "PassengerWanted"
    WARRANT             = "Warrant"


class GuiFocus(int, Enum):
    NO_FOCUS            = 0
    INTERNAL_PANEL      = 1     # левая панель
    EXTERNAL_PANEL      = 2     # правая панель
    COMMS_PANEL         = 3
    ROLE_PANEL          = 4
    STATION_SERVICES    = 5
    GALAXY_MAP          = 6
    SYSTEM_MAP          = 7
    ORRERY              = 8
    FSS_MODE            = 9
    SAA_MODE            = 10
    CODEX               = 11


class _FlagsBase:
    def __init__(self):
        self._raw = 0

    def update(self, val: int):
        self._raw = val


class _Flag:
    def __init__(self, value):
        self.value = value

    def __get__(self, instance, owner):
        if instance is None:
            return self.value
        return bool(instance._raw & self.value)


class Flags(_FlagsBase):
    DOCKED                  = _Flag(1 << 0)
    LANDED                  = _Flag(1 << 1)
    LANDING_GEAR_DOWN       = _Flag(1 << 2)
    SHIELDS_UP              = _Flag(1 << 3)
    SUPERCRUISE             = _Flag(1 << 4)
    FLIGHT_ASSIST_OFF       = _Flag(1 << 5)
    HARDPOINTS_DEPLOYED     = _Flag(1 << 6)
    IN_WING                 = _Flag(1 << 7)
    LIGHTS_ON               = _Flag(1 << 8)
    CARGO_SCOOP_DEPLOYED    = _Flag(1 << 9)
    SILENT_RUNNING          = _Flag(1 << 10)
    SCOOPING_FUEL           = _Flag(1 << 11)
    SRV_HANDBRAKE           = _Flag(1 << 12)
    SRV_TURRET_VIEW         = _Flag(1 << 13)
    SRV_TURRET_RETRACKED    = _Flag(1 << 14)
    SRV_DRIVE_ASSIST        = _Flag(1 << 15)
    FSD_MASS_LOCKED         = _Flag(1 << 16)
    FSD_CHARGING            = _Flag(1 << 17)
    FSD_COOLDOWN            = _Flag(1 << 18)
    LOW_FUEL                = _Flag(1 << 19)    # <25%
    OVERHEATING             = _Flag(1 << 20)    # >100%
    HAS_LAT_LONG            = _Flag(1 << 21)
    IS_IN_DANGER            = _Flag(1 << 22)
    BEING_INTERDICTED       = _Flag(1 << 23)
    IN_MAIN_SHIP            = _Flag(1 << 24)
    IN_FIGHTER              = _Flag(1 << 25)
    IN_SRV                  = _Flag(1 << 26)
    HUD_IN_ANALYSIS_MODE    = _Flag(1 << 27)
    NIGHT_VISION            = _Flag(1 << 28)
    ALT_FROM_AVERAGE_RADIUS = _Flag(1 << 29)
    FSD_JUMP                = _Flag(1 << 30)
    SRV_HIGH_BEAM           = _Flag(1 << 31)


class Flags2(_FlagsBase):
    ON_FOOT                 = _Flag(1 << 0)
    IN_TAXI                 = _Flag(1 << 1)     # или в десантном шаттле
    IN_MULTICREW            = _Flag(1 << 2)     # т.е. в чужом корабле
    ON_FOOT_IN_STATION      = _Flag(1 << 3)
    ON_FOOT_ON_PLANET       = _Flag(1 << 4)
    AIM_DOWN_SIGHT          = _Flag(1 << 5)
    LOW_OXYGEN              = _Flag(1 << 6)
    LOW_HEALTH              = _Flag(1 << 7)
    COLD                    = _Flag(1 << 8)
    HOT                     = _Flag(1 << 9)
    VERY_COLD               = _Flag(1 << 10)
    VERY_HOT                = _Flag(1 << 11)
    GLIDE_MODE              = _Flag(1 << 12)
    ON_FOOT_IN_HANGAR       = _Flag(1 << 13)
    ON_FOOT_SOCIAL_SPACE    = _Flag(1 << 14)
    ON_FOOT_EXTERIOR        = _Flag(1 << 15)
    BREATHABLE_ATMOSPHERE   = _Flag(1 << 16)
    TELEPRESENCE_MULTICREW  = _Flag(1 << 17)
    PHYSICAL_MULTICREW      = _Flag(1 << 18)
    FSD_HYPERDRIVE_CHARGING = _Flag(1 << 19)


@dataclass
class GameState:
    """
    Хранит текущее состояние игры, включая полную репрезентацию status.json.
    """
    # параметры
    cmdr: str                   = None
    squadron: str               = None
    legacy_sqid: str            = None

    odyssey: bool               = None
    game_in_beta: bool          = None
    pips: list[int, int, int]   = None
    firegroup: int              = None
    gui_focus: GuiFocus         = None
    fuel_main: float            = None
    fuel_reservoir: float       = None
    cargo: int                  = None
    legal_state: LegalState     = None
    balance: int                = None
    destination: str            = None

    system: str                 = None
    system_address: int         = None
    system_coords: 'Coords'     = None
    pending_jump_system: str    = None
    pending_jump_system_id: int = None
    station: str                = None
    body_name: str              = None
    latitude: float             = None
    longitude: float            = None
    altitude: int               = None
    heading: int                = None
    planet_radius: float        = None

    # пешие параметры
    oxygen: float               = None      # (0.0 .. 1.0)
    health: float               = None      # (0.0 .. 1.0)
    temperature: int            = None      # в кельвинах
    selected_weapon: str        = None
    gravity: float              = None

    # флаги
    flags = Flags()
    flags2 = Flags2()
