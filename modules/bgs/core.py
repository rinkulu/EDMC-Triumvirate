from context import PluginContext
from modules.lib.module import Module

from . import submodule_base

# isort: off
import functools
_translate = functools.partial(PluginContext._tr_template, filepath=__file__)
# isort: on


class BGSCore(Module):
    localized_name = _translate("BGS module")

    def __init__(self):
        submodule_base.init_submodules(self)
        self.submodules = submodule_base.get_submodules()

    def on_journal_entry(self, entry):
        return super().on_journal_entry(entry)
