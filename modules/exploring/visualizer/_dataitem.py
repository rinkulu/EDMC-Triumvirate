import re
from modules.lib.module import Module


# Изначально предполагалось, что эта штука будет в model.py,
# но из-за проблемы рекурсивного импорта пришлось вынести её в отдельный файл.

class _DataItem:
    _BODY_PATTERN = re.compile(r"([A-Z]+\s)*\d+(\s[a-z])*$")

    def __init__(self, module: Module, category: str, body: str, text: str, no_shrink: bool = False):
        if not no_shrink:
            re_match = re.search(self._BODY_PATTERN, body)
            if re_match:
                # нам дали название тела вместе с именем системы - уберём лишнее
                body = re_match.group()

        self.m_qualname = module.__class__.__qualname__
        self.category   = category
        self.body       = body
        self.text       = text

    def __lt__(self, other: '_DataItem') -> bool:
        if self.category != other.category:
            return self.category < other.category
        if self.body != other.body:
            return self.body < other.body
        return self.text < other.text

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _DataItem):
            return NotImplemented
        # одинаковую инфу из разных модулей будем считать равной - это нужно для упрощения кода ui
        return (self.category, self.body, self.text) == (other.category, other.body, other.text)

    def __hash__(self) -> int:
        # аналогично - модуль-источник не будет давать уникальности
        return hash((self.category, self.body, self.text))
