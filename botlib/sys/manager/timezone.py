# -*- coding: utf-8 -*-
# botlib/sys/manager/localization.py

from botlib.sys.config import Config
from enum import Enum, unique
from os.path import join as path_combine
from XProperties import Properties

__all__ = ["Locale", "LocaleProperties"]

_LOCALE_PATH = path_combine(Config.get("BASE_PATH"), Config.get("LOCALE_PATH"))


@unique
class Locale(Enum):
    NONE = "none"
    ENGLISH = "en"
    KOREAN = "ko"


class LocaleProperties:
    def __init__(self, name: str, locale: Locale = Locale.NONE):
        self._name = name
        self._current_locale = locale

    def get(self, key: str) -> str | None:
        if self._current_locale == Locale.NONE:
            filename = f"{self._name}.xml"
        else:
            filename = f"{self._name}_{self._current_locale.value}.xml"
        path = path_combine(_LOCALE_PATH, filename)
        prop = Properties()
        prop.load_from_xml(path)
        return prop.get_property(key, "NaN")

    @property
    def current_locale(self) -> Locale:
        return self._current_locale
