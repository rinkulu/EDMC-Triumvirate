from abc import ABC
from typing import TYPE_CHECKING, final


if TYPE_CHECKING:
    from modules.bgs.core import BGSCore


class BGSSubmodule(ABC):
    core: 'BGSCore'

    @final
    def send_bgs_report(self, url: str, params: dict, affected_systems: str | list[str]):
        self.core._send_data(url, params, affected_systems, self.__class__.__qualname__)
