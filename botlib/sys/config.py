# -*- coding: utf-8 -*-
# botlib/sys/config.py

from os import environ
from os.path import exists
from XProperties import Properties

__all__ = ["Config"]

SYSTEM_CONFIG_PATH = environ.get("HOLOBOT_CONF_PATH", "global-configure.conf")


# initialize configure
if not exists(SYSTEM_CONFIG_PATH):
    prop = Properties()
    prop.load(SYSTEM_CONFIG_PATH[:-5] + "-example.conf")
    for key in prop.keys():
        message = input(f"{key}=")
        if message:
            prop[key] = message
    prop.save(SYSTEM_CONFIG_PATH)


class Config:
    @staticmethod
    def get(config: str) -> str:
        prop = Properties()
        prop.load(SYSTEM_CONFIG_PATH)
        return prop[config]
