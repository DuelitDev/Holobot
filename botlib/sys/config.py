# -*- coding: utf-8 -*-
# botlib/sys/config.py

from XProperties import Properties

__all__ = ["Config"]

SYSTEM_CONFIG_PATH = "global-configure.conf"


class Config:
    @staticmethod
    def get(config: str) -> str:
        prop = Properties()
        prop.load(SYSTEM_CONFIG_PATH)
        return prop[config]
