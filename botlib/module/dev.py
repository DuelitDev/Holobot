# -*- coding: utf-8 -*-
# botlib/module/dev.py


from botlib.sys.config import Config
from botlib.sys.manager import Locale, StorageManager
from botlib.sys.util import discord_command, discord_command_wrapper
from discord.ext.commands import Context
from os.path import join as path_combine

__all__ = ["Dev", "_get_server_conf"]

_SERVER_CONF_ENTRY = Config.get("SERVER_CONF_ENTRY")


async def _get_server_conf(ctx: Context, only_admin: bool = True) -> dict:
    path = path_combine(_SERVER_CONF_ENTRY, f"{ctx.guild.id}.json")
    if not StorageManager().exists(path):
        await ctx.send("You have not yet registered your server.")
        return {}
    temp = __import__("json").loads(StorageManager().get(path))
    if str(ctx.author.id) != temp["AdminID"] and only_admin:
        await ctx.send(f"Operation not permitted.")
        return {}
    return temp


async def _save_server_conf(ctx: Context, data: dict) -> bool:
    if str(ctx.author.id) != data["AdminID"]:
        await ctx.send(f"Operation not permitted.")
        return False
    path = path_combine(_SERVER_CONF_ENTRY, f"{ctx.guild.id}.json")
    if not StorageManager().exists(path):
        await ctx.send("You have not yet registered your server.")
        return False
    StorageManager().put(path, __import__("json").dumps(data))
    return True


@discord_command_wrapper("janken", add_namespace=True)
class _DevJankenWrap:
    @staticmethod
    @discord_command("limit")
    async def limit(ctx: Context, operation: str | None = None):
        conf = await _get_server_conf(ctx)
        if not conf:
            return
        if operation is None:
            await ctx.send(f"Limit is set to: {conf['Janken']['Limit']}")
            return
        if operation == "enable":
            conf["Janken"]["Limit"] = True
        elif operation == "disable":
            conf["Janken"]["Limit"] = False
        else:
            await ctx.send(f"Operation must be 'enable' or 'disable'.")
            return
        if not await _save_server_conf(ctx, conf):
            return
        await ctx.send(f"Janken: day limit {operation}d.")


@discord_command_wrapper("dev", add_namespace=True)
class Dev:
    @staticmethod
    @discord_command("ping")
    async def ping(ctx: Context):
        await ctx.send("pong")

    @staticmethod
    @discord_command("register")
    async def register(ctx: Context):
        path = path_combine(_SERVER_CONF_ENTRY, f"{ctx.guild.id}.json")
        if not StorageManager().exists(path):
            conf = __import__("json").dumps({
                "AdminID": str(ctx.author.id),
                "Locale": Locale.NONE.value,
                "Janken": {"Limit": True}
            })
            StorageManager().put(path, conf)
            await ctx.send("Registration Complete.")
            await ctx.send(f"User {ctx.author.id} is now administrator.")
        else:
            await ctx.send("Registration has already been completed.")

    @staticmethod
    @discord_command("locale")
    async def locale(ctx: Context, locale: str | None = None):
        conf = await _get_server_conf(ctx)
        if not conf:
            return
        if locale is not None:
            locale = locale.lower()
            if locale not in [i.value for i in Locale]:
                await ctx.send(f"'{locale}' is not a valid locale")
                return
            conf["Locale"] = str(Locale(locale).value)
            if not await _save_server_conf(ctx, conf):
                return
        await ctx.send(f"Locale is set to: {conf['Locale']}")

    @staticmethod
    @discord_command("get_all_locales")
    async def get_all_locales(ctx: Context):
        await ctx.send(", ".join([str(locale.value) for locale in Locale]))

    @property
    def janken(self) -> _DevJankenWrap:
        return _DevJankenWrap()
