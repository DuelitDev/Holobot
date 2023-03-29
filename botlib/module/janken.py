# -*- coding: utf-8 -*-
# botlib/module/janken.py

from botlib.module.dev import _get_server_conf
from botlib.sys.config import Config
from botlib.sys.manager import Locale, LocaleProperties, StorageManager
from botlib.sys.util import discord_command, discord_command_wrapper
from datetime import datetime
from discord import Embed, File
from discord.ext.commands import Context
from enum import Enum, IntEnum
from json import loads as loads_json
from os.path import join as path_combine
from re import findall as findall_regexp
from sqlite3 import connect as connect_db
from uuid import uuid4

__all__ = ["Janken"]

_BASE_PATH = Config.get("BASE_PATH")
_CACHE_PATH = path_combine(_BASE_PATH, Config.get("CACHE_PATH"))
_LOCALE_PATH = path_combine(_BASE_PATH, Config.get("LOCALE_PATH"))
_JANKEN_DATA_ENTRY = Config.get("JANKEN_DATA_ENTRY")
_JANKEN_RESOURCE_ENTRY = Config.get("JANKEN_RESOURCE_ENTRY")


def _get_command_info() -> dict:
    base_locale = LocaleProperties("janken", Locale.NONE)
    other = [LocaleProperties("janken", i).get("Command_Alias") for i in Locale]
    alias = eval("+".join(other))
    return {"command_name": base_locale.get("Command"), "alias": alias}


def _get_janken_db() -> str:
    key = path_combine(_JANKEN_DATA_ENTRY, "janken.sqlite")
    return StorageManager().get_to_file(key)


def _save_janken_db():
    key = path_combine(_JANKEN_DATA_ENTRY, "janken.sqlite")
    path = path_combine(_CACHE_PATH, key)
    StorageManager().put_from_file(key, path)


class JankenType(IntEnum):
    Rock = 0
    Scissors = 1
    Paper = 2


class JankenResult(Enum):
    Win = "Win"
    Lose = "Lose"
    Draw = "Draw"


class Record:
    def __init__(self, result: JankenResult, date: datetime):
        self._result = result
        self._date = date

    @property
    def result(self) -> JankenResult:
        return self._result

    @property
    def date(self) -> datetime:
        return self._date


class JankenRecorder:
    _instance = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        # single-ton pattern
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # single-ton
        if self._initialized:
            return
        self._initialized = True
        self._db_connect = connect_db(_get_janken_db())
        self._cursor = self._db_connect.cursor()

    def write(self, user_id: str, result: JankenResult):
        self._cursor.execute(
            "INSERT INTO Records (id, result, date) VALUES (?, ?, ?)",
            (user_id, result.value, datetime.now().strftime("%Y-%m-%d"))
        )
        self._db_connect.commit()

    def read_all(self, user_id: str) -> list[Record]:
        self._cursor.execute(
            f"SELECT * FROM Records WHERE id={user_id} ORDER BY date DESC"
        )
        records = [
            Record(JankenResult(result), datetime.strptime(date, "%Y-%m-%d"))
            for _, result, date in self._cursor.fetchall()
        ]
        return records

    def read_one(self, user_id: str) -> Record | None:
        records = self.read_all(user_id)
        if not records:
            return None
        return records[0]


@discord_command_wrapper()
class Janken:
    @discord_command(**_get_command_info())
    async def handler(self, ctx: Context, command: str = "", *args, **kwargs):
        conf = await _get_server_conf(ctx, only_admin=False)
        locale = LocaleProperties("janken", Locale(conf["Locale"]))
        command = command.lower()
        match command.lower():
            case cmd if cmd in eval(locale.get("Command_Rock")):
                await self.game(ctx, locale, JankenType.Rock)
            case cmd if cmd in eval(locale.get("Command_Scissors")):
                await self.game(ctx, locale, JankenType.Scissors)
            case cmd if cmd in eval(locale.get("Command_Paper")):
                await self.game(ctx, locale, JankenType.Paper)
            case cmd if cmd in eval(locale.get("Command_Record")):
                await self.record(ctx, locale, *args, **kwargs)
            case cmd if cmd in eval(locale.get("Command_Help")):
                await self.help(ctx, locale)
            case _:
                await self.help(ctx, locale)

    @staticmethod
    async def game(ctx: Context, locale: LocaleProperties, choice: JankenType):
        user_id = str(ctx.author.id)
        conf = await _get_server_conf(ctx, only_admin=False)
        record = JankenRecorder().read_one(user_id)
        if (record and conf["Janken"]["Limit"] and
                86400 > (datetime.now() - record.date).total_seconds()):
            await ctx.send(locale.get("Janken_NextDay"))
            return
        bot_choice = JankenType(__import__("random").randint(0, 999999999) % 3)
        compare_table = {0: {0: "Draw", 1: "Win", 2: "Lose"},
                         1: {0: "Lose", 1: "Draw", 2: "Win"},
                         2: {0: "Win", 1: "Lose", 2: "Draw"}}
        result = JankenResult(compare_table[choice][bot_choice])
        JankenRecorder().write(user_id, result)
        key = path_combine(_JANKEN_RESOURCE_ENTRY, f"{bot_choice}/Default.mp4")
        path = StorageManager().get_to_file(key)
        await ctx.reply(file=File(path, filename=f"{uuid4()}.mp4"))

    @staticmethod
    async def record(ctx: Context, locale: LocaleProperties, query: str = ":5"):
        records = JankenRecorder().read_all(str(ctx.author.id))
        total = [0, 0, 0]
        for record in records:
            if record.result == JankenResult.Win:
                total[0] += 1
            elif record.result == JankenResult.Lose:
                total[1] += 1
            elif record.result == JankenResult.Draw:
                total[2] += 1
        win_rate = total[0] / len(records) * 100
        author = f"{ctx.author.name}#{ctx.author.discriminator}"
        title = locale.get("Record_Title").format(author)
        subtitle = locale.get("Record_Subtitle").format(*total, win_rate)
        try:
            fields = []
            indexer = findall_regexp("(^[0-9]*:?[0-9]*:?[0-9]*)", query)
            assert indexer
            records = eval(f"records[{indexer[0]}]")
            for record in records:
                result = locale.get(f"Record_{record.result.value}")
                text = locale.get("Record_Field").format(
                    record.date.year, record.date.month, record.date.day, result
                )
                fields.append(text)
        except (AssertionError, ValueError, SyntaxError):
            fields = [locale.get("Record_InvalidIndexer").format(query)]
        except IndexError:
            fields = [locale.get("Record_OutOfRange")]
        embed = Embed(title=title, description=subtitle, color=0x82e6e6)
        for field in fields:
            embed.add_field(name=field, value="** **", inline=False)
        await ctx.send(embed=embed)

    @staticmethod
    async def help(ctx: Context, locale: LocaleProperties):
        embed = Embed(title=locale.get("Help_Title"), color=0x82e6e6)
        descriptions = loads_json(locale.get("Help_Field"))
        for description in descriptions:
            description["value"] = "\n".join(description["value"])
            embed.add_field(**description, inline=False)
        await ctx.send(embed=embed)
