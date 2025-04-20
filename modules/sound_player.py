"""
Проигрыватель звуковых файлов.
"""

from context import PluginContext
from modules.lib.thirdparty.playsound import playsound


class Player:
    DEFAULT_SOUNDS_LOCATION = PluginContext.plugin_dir / "sounds"
    USER_CUSTOM_SOUNDS_LOCATION = PluginContext.plugin_dir / "userdata" / "sounds"

    def play_info(self, block: bool = False):
        playsound(self.DEFAULT_SOUNDS_LOCATION / "info.wav", block)

    def play_success(self, block: bool = False):
        playsound(self.DEFAULT_SOUNDS_LOCATION / "success.wav", block)

    def play_warning(self, block: bool = False):
        playsound(self.DEFAULT_SOUNDS_LOCATION / "warning.wav", block)

    def play_error(self, block: bool = False):
        playsound(self.DEFAULT_SOUNDS_LOCATION / "error.wav", block)

    def play(self, name: str, block: bool = False):
        path = self.USER_CUSTOM_SOUNDS_LOCATION / name
        playsound(path, block)
