import sys
from typing import TYPE_CHECKING

from Triumvirate.core.context import PluginContext


def _translate(x: str, lang: str | None = None) -> str:
    filename = sys._getframe(1).f_code.co_filename
    return PluginContext._tr_template(x=x, filepath=filename, lang=lang)


if TYPE_CHECKING:
    debug = PluginContext.logger.debug
    info = PluginContext.logger.info
    warning = PluginContext.logger.warning
    error = PluginContext.logger.error
    critical = PluginContext.logger.critical
else:
    def __make_logger_proxy(level_name: str):
        def wrapper(*args, **kwargs):
            kwargs["stacklevel"] = kwargs.get("stacklevel", 1) + 1
            # Чиним неправильное определение функции, пишущей логи. Спасибо разрабам EDMC, игнорящим stacklevel.
            extra = kwargs.setdefault("extra", {})
            extra["qualname"] = sys._getframe(1).f_code.co_qualname
            return getattr(PluginContext.logger, level_name)(*args, **kwargs)
        return wrapper

    debug = __make_logger_proxy("debug")
    info = __make_logger_proxy("info")
    warning = __make_logger_proxy("warning")
    error = __make_logger_proxy("error")
    critical = __make_logger_proxy("critical")
