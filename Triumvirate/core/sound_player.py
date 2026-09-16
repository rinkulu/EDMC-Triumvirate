import functools
import platform
import shutil
import subprocess
import threading
from enum import StrEnum
from pathlib import Path

from Triumvirate.core.context import PluginContext


class SoundType(StrEnum):
    INFO = "info.wav"
    SUCCESS = "success.wav"
    WARNING = "warning.wav"
    ERROR = "error.wav"


class SoundPlayer:
    """
    Проигрыватель звуковых файлов. Поддерживает ряд встроенных (см. `SoundType`)
    и пользовательские, помещённые в userdata.
    """
    DEFAULT_SOUNDS_LOCATION = PluginContext.paths.assets_dir / "sounds"
    USER_CUSTOM_SOUNDS_LOCATION = PluginContext.paths.userdata_dir / "sounds"

    def __init__(self):
        match platform.system():
            case "Windows":
                self.__implementation = self.__playsound_win
            case "Darwin":
                self.__implementation = functools.partial(self.__playsound_nix, cmd=["afplay"])
            case _:  # *nix
                backends = [
                    ["mpv", "--no-terminal", "--really-quiet", "--no-config"],
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
                    ["cvlc", "-Idummy", "--no-video", "--play-and-exit", "-q"],  # VLC: high latency
                    ["gst-play-1.0", "--no-interactive", "--quiet"],  # GStreamer: WAV guaranteed, mp3 likely
                    ["play", "-q"],  # SoX: WAV guaranteed, mp3 depends (distro, installed packages)
                    ["pw-play"],  # PipeWire: WAV guaranteed, mp3 unlikely (compilation options)
                    ["paplay"],  # PulseAudio: same
                    ["aplay"],  # ALSA: only WAV
                ]
                for cmd in backends:
                    if shutil.which(cmd[0]):
                        PluginContext.logger.info(f"Chosen player backend: {cmd[0]}")
                        self.__implementation = functools.partial(self.__playsound_nix, cmd=cmd)
                        break
                else:
                    PluginContext.logger.warning("No available player backends found, SoundPlayer will be disabled.")
                    self.__implementation = lambda path: None


    def play_info(self):
        self._playsound(self.DEFAULT_SOUNDS_LOCATION / SoundType.INFO)

    def play_success(self):
        self._playsound(self.DEFAULT_SOUNDS_LOCATION / SoundType.SUCCESS)

    def play_warning(self):
        self._playsound(self.DEFAULT_SOUNDS_LOCATION / SoundType.WARNING)

    def play_error(self):
        self._playsound(self.DEFAULT_SOUNDS_LOCATION / SoundType.ERROR)

    def play_inbuilt(self, sound: SoundType):
        match sound:
            case SoundType.INFO: self.play_info()
            case SoundType.SUCCESS: self.play_success()
            case SoundType.WARNING: self.play_warning()
            case SoundType.ERROR: self.play_error()
            case _: raise ValueError(f"Unknown sound type: {sound!r}")

    def play_custom(self, name: str):
        self._playsound(self.USER_CUSTOM_SOUNDS_LOCATION / name)


    def _playsound(self, path: Path):
        if not (path.exists() and path.is_file()):
            PluginContext.logger.error(f"Can't play sound {path}: file does not exist")
            return
        self.__implementation(path)

    @staticmethod
    def __playsound_win(path: Path):
        def __inner():
            import ctypes
            import random
            mci_send = ctypes.windll.winmm.mciSendStringW  # type: ignore
            mci_error = ctypes.windll.winmm.mciGetErrorStringW  # type: ignore

            def check_error(err_code: int):
                if err_code != 0:
                    buf = ctypes.create_unicode_buffer(256)
                    mci_error(err_code, buf, 256)
                    PluginContext.logger.error(f"Failed to play sound {path} - MCI error: code {err_code}, message {buf.value!r}")
                    return False
                return True

            alias = f"edmctrmv_snd_{random.randint(10000, 99999)}"
            err = mci_send(f'open "{path.resolve()}" alias {alias}', None, 0, 0)
            if not check_error(err):
                return
            try:
                err = mci_send(f'play {alias} wait', None, 0, 0)
                check_error(err)
            finally:
                mci_send(f'close {alias}', None, 0, 0)

        threading.Thread(target=__inner, daemon=True).start()

    @staticmethod
    def __playsound_nix(path: Path, cmd: list[str]):
        def __inner():
            try:
                proc = subprocess.Popen(
                    cmd + [str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                _, stderr = proc.communicate()
                if proc.returncode != 0:
                    err_msg = stderr.strip() if stderr else f"exit code {proc.returncode}"
                    PluginContext.logger.error(f"Failed to play sound {path} via {cmd[0]}: {err_msg}")
            except Exception as e:
                PluginContext.logger.error(f"Failed to play sound {path} - subprocess error:", exc_info=e)

        threading.Thread(target=__inner, daemon=True).start()
