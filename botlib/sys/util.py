# -*- coding: utf-8 -*-
# botlib/sys/util.py

from discord.ext.commands import Bot, Command


def discord_command_wrapper(namespace: str = "", add_namespace: bool = False):
    def wrapper(obj):
        obj._discord_command_wrapper = True
        obj._discord_command_wrapper_namespace = namespace
        obj._discord_command_wrapper_add_namespace = add_namespace
        return obj

    return wrapper


def discord_command(command_name: str, alias: tuple[str] = ()):
    def wrapper(obj):
        obj._discord_command = True
        obj._discord_command_name = command_name
        obj._discord_command_alias = alias
        return obj

    return wrapper


def add_all_commands(bot: Bot, wrapper: object, base: str = ""):
    for key in dir(wrapper):
        attr = getattr(wrapper, key)
        if hasattr(attr, "_discord_command"):
            namespace = getattr(wrapper, "_discord_command_wrapper_namespace")
            name = getattr(attr, "_discord_command_name")
            alias = getattr(attr, "_discord_command_alias")
            if getattr(wrapper, "_discord_command_wrapper_add_namespace"):
                name = f"{base}.{namespace}.{name}"[1:]
                aliases = tuple([f"{base}.{namespace}.{i}"[1:] for i in alias])
            else:
                name = f"{base}.{name}"[1:]
                aliases = tuple([f"{base}.{i}"[1:] for i in alias])
            bot.add_command(Command(name=name, aliases=aliases, func=attr))
        elif hasattr(attr, "_discord_command_wrapper") and key != "__class__":
            namespace = getattr(wrapper, "_discord_command_wrapper_namespace")
            add_all_commands(bot, attr, f"{base}.{namespace}")
