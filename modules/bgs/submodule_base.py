from abc import ABC, ABCMeta
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .core import BGSCore


class SubmoduleMeta(ABCMeta):
    _submodules = set()
    _instances = set()

    def __new__(cls, name: str, bases: tuple, dct: dict):
        submodule = super().__new__(cls, name, bases, dct)
        if ABC not in bases:
            cls._submodules.add(submodule)
        return submodule

    def __call__(cls):
        raise RuntimeError("BGS Submodules cannot be created outside of the BGSCore class.")

    @classmethod
    def init_submodules(cls, core: 'BGSCore'):
        def rowgen():
            row = 0
            while True:
                yield row
                row += 1

        rg = rowgen()
        for subm in cls._submodules:
            subm.core = core
            subm._ui_row = next(rg)
            instance = super().__call__(subm)
            cls._instances.add(instance)


class Submodule(ABC, metaclass=SubmoduleMeta):
    core: 'BGSCore'
    _ui_row: int

    def on_journal_entry(self, entry: dict):
        """
        Вызывается при появлении новой записи в логах.
        В отличие от Module.on_journal_entry, принимает запись "как есть"
        и должен полагаться на данные контекста для получения дополнительной информации.
        """

    def on_dashboard_entry(self):
        """
        Вызывается при обновлении Status.json
        В отличие от Module.on_dashboard_entry, служит лишь сигналом обновления файла.
        Субмодуль должен получать данные из context.GameState
        """


    def on_close(self):
        """
        Вызывается при завершении работы EMDC.
        """


def init_submodules(core: 'BGSCore'):
    # НЕ ТРОГАТЬ

    # isort: off
    import importlib
    from .submodules import __all__ as subm_list
    # isort: on
    for submodule in (f"modules.bgs.submodules.{mod}" for mod in subm_list):
        importlib.import_module(submodule)
    SubmoduleMeta.init_submodules(core)


def get_submodules() -> list[Submodule]:
    return list(SubmoduleMeta._instances)
