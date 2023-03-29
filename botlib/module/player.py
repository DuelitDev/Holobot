# -*- coding: utf-8 -*-
# botlib/module/player.py

from __future__ import annotations
from botlib.module.dev import _get_server_conf
from botlib.sys.config import Config
from botlib.sys.manager import Locale, LocaleProperties, StorageManager
from botlib.sys.util import discord_command, discord_command_wrapper
from collections import deque as queue
from discord import Embed, FFmpegOpusAudio
from discord.ext.commands import Context
from json import loads as loads_json
from os import makedirs
from os.path import join as path_combine
from whoosh.analysis import FancyAnalyzer
from whoosh.fields import ID, Schema, TEXT
from whoosh.index import create_in
from whoosh.qparser import MultifieldParser

__all__ = ["Player"]

_BASE_PATH = Config.get("BASE_PATH")
_INDEX_PATH = path_combine(_BASE_PATH, Config.get("INDEX_PATH"))
_PLAYER_DATA_ENTRY = Config.get("PLAYER_DATA_ENTRY")
_PLAYER_RESOURCE_ENTRY = Config.get("PLAYER_RESOURCE_ENTRY")


def _get_command_info() -> dict:
    base_locale = LocaleProperties("player", Locale.NONE)
    other = [LocaleProperties("player", i).get("Command_Alias") for i in Locale]
    alias = eval("+".join(other))
    return {"command_name": base_locale.get("Command"), "alias": alias}


class Music:
    def __init__(self, title: str, authors: str, alias: str, id_: str):
        self._title = title
        self._authors: tuple[str] = tuple(authors.split(", "))
        self._alias = alias
        self._id = id_
        self._author_code = id_[0:2]
        self._music_code = id_[2:4]

    @staticmethod
    def analyze_id(id_: str) -> tuple[str, str]:
        author_id = id_[0:2]
        music_id = id_[2:4]
        return author_id, music_id

    @staticmethod
    def create(locale: Locale, id_: str) -> Music:
        author_id, music_id = Music.analyze_id(id_)
        key = path_combine(_PLAYER_RESOURCE_ENTRY, author_id,
                           f"schema_{str(locale.value)}.json")
        schema = __import__("json").loads(StorageManager().get(key))[music_id]
        return Music(schema["title"], ", ".join(schema["authors"]),
                     schema["alias"], schema["id"])

    @staticmethod
    def get_resource(id_: str) -> str:
        author_id, music_id = Music.analyze_id(id_)
        key = path_combine(_PLAYER_RESOURCE_ENTRY,
                           f"{author_id}/{music_id}/resource.webm")
        return StorageManager().get_to_file(key)

    @staticmethod
    def get_thumbnail_url(id_: str) -> str:
        author_id, music_id = Music.analyze_id(id_)
        key = path_combine(_PLAYER_RESOURCE_ENTRY,
                           f"{author_id}/{music_id}/thumbnail.webp")
        return StorageManager().format_key_to_url(key)

    @property
    def title(self) -> str:
        return self._title

    @property
    def authors(self) -> tuple[str]:
        return self._authors

    @property
    def alias(self) -> str:
        return self._alias

    @property
    def id(self) -> str:
        return self._id


class MusicSearcher:
    _instance = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        # single-ton pattern
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # single-ton
        if self._initialized:
            return
        self._initialized = True
        analyzer = FancyAnalyzer()
        self._schema = Schema(
            title=TEXT(analyzer=analyzer, stored=True, field_boost=2),
            authors=TEXT(analyzer=analyzer, stored=True, field_boost=1.5),
            alias=TEXT(analyzer=analyzer, stored=True, field_boost=1.2),
            id_=ID(stored=True, field_boost=0.05))
        self._indexes = {}
        root = path_combine(_PLAYER_RESOURCE_ENTRY, "root.json")
        root_schema = __import__("json").loads(StorageManager().get(root))
        for locale in Locale:
            if locale == Locale.NONE:
                continue
            index_path = path_combine(_INDEX_PATH, str(locale.value))
            makedirs(index_path, exist_ok=True)
            index = create_in(index_path, self._schema)
            writer = index.writer()
            for author in root_schema["authors"]:
                key = path_combine(_PLAYER_RESOURCE_ENTRY, author,
                                   f"schema_{str(locale.value)}.json")
                schema = __import__("json").loads(StorageManager().get(key))
                for music in schema.values():
                    writer.add_document(title=music["title"],
                                        authors=", ".join(music["authors"]),
                                        alias=music["alias"],
                                        id_=music["id"])
            writer.commit()
            self._indexes[locale] = index

    def search(self, request: str, locale: Locale) -> list[Music]:
        with self._indexes[locale].searcher() as searcher:
            parser = MultifieldParser(
                ["title", "authors", "alias", "id_"],
                self._schema
            )
            query = parser.parse(request)
            result = list(searcher.search(query))
            sorted(result, key=lambda hit: hit.score, reverse=True)
            musics = [Music(**hit.fields()) for hit in result]
            return musics


class MusicQueue:
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
        self._queue: dict[int, queue] = {}
        self._latest: dict[int, Music | None] = {}
        self._is_loop: dict[int, bool] = {}

    def add(self, ctx, source):
        id_ = ctx.guild.id
        if id_ not in self._queue:
            self._queue[id_] = queue()
            self._latest[id_] = None
            self._is_loop[id_] = False
        self._queue[id_].append(source)

    def peek(self, ctx):
        id_ = ctx.guild.id
        if id_ not in self._queue:
            raise RuntimeError("Queue removed.")
        source = self._queue[id_][0]
        return source

    def pop(self, ctx):
        id_ = ctx.guild.id
        if id_ not in self._queue:
            raise RuntimeError("Queue removed.")
        source = self._queue[id_].popleft()
        self._latest[id_] = source
        if self._is_loop[id_]:
            self._queue[id_].append(source)

    def all(self, ctx):
        id_ = ctx.guild.id
        if id_ not in self._queue:
            raise RuntimeError("Queue removed.")
        return self._queue[id_]

    def latest(self, ctx):
        id_ = ctx.guild.id
        if id_ not in self._queue:
            raise RuntimeError("Queue removed.")
        return self._latest[id_]

    def is_exist(self, ctx):
        return ctx.guild.id in self._queue

    def loop(self, ctx, is_loop: bool):
        id_ = ctx.guild.id
        if id_ not in self._is_loop:
            return
        self._is_loop[id_] = is_loop

    def is_loop(self, ctx):
        id_ = ctx.guild.id
        if id_ not in self._queue:
            return False
        return self._is_loop[id_]

    def is_empty(self, ctx):
        id_ = ctx.guild.id
        if id_ not in self._queue:
            return True
        return not len(self._queue[id_]) > 0

    def free(self, ctx):
        id_ = ctx.guild.id
        if id_ in self._queue:
            del self._queue[id_]
            del self._latest[id_]
            del self._is_loop[id_]


@discord_command_wrapper()
class Player:
    @discord_command(**_get_command_info())
    async def handler(self, ctx: Context, command: str = "", *args, **kwargs):
        conf = await _get_server_conf(ctx, only_admin=False)
        locale = LocaleProperties("player", Locale(conf["Locale"]))
        command = command.lower()
        match command.lower():
            case cmd if cmd in eval(locale.get("Command_Play")):
                await self.play(ctx, locale, *args, **kwargs)
            case cmd if cmd in eval(locale.get("Command_Leave")):
                await self.leave(ctx)
            case cmd if cmd in eval(locale.get("Command_Search")):
                await self.search(ctx, locale, *args, **kwargs)
            case cmd if cmd in eval(locale.get("Command_Loop")):
                await self.loop(ctx, locale)
            case cmd if cmd in eval(locale.get("Command_Queue")):
                await self.queue(ctx, locale)
            case cmd if cmd in eval(locale.get("Command_Help")):
                await self.help(ctx, locale)
            case _:
                await self.help(ctx, locale)

    @staticmethod
    async def play(ctx: Context, locale: LocaleProperties, id_: str):
        if ctx.author.voice and ctx.author.voice.channel:
            channel = ctx.author.voice.channel
            if not ctx.voice_client or not channel == ctx.voice_client.channel:
                if ctx.guild.voice_client:
                    await ctx.guild.voice_client.disconnect(force=True)
                    print("disconnected")
                await channel.connect()  # noqa
            voice = ctx.voice_client
        else:
            await ctx.send(locale.get("Play_JoinVoiceChannelFirst"))
            return
        try:
            music = Music.create(locale.current_locale, id_)
            MusicQueue().add(ctx, music)
            if not voice.is_playing():
                await Player._play_next(ctx, locale)
            else:
                embed = Embed(title=locale.get("Play_AddQueue"),
                              description=music.title, color=0x82e6e6)
                embed.set_thumbnail(url=Music.get_thumbnail_url(music.id))
                await ctx.send(embed=embed)
        except ValueError as e:
            print(e)
            await ctx.send(locale.get("Play_InvalidID").format(id_))

    @staticmethod
    async def _play_next(ctx, locale, pop: bool = False):
        if not MusicQueue().is_empty(ctx):
            if pop:
                MusicQueue().pop(ctx)
            music = MusicQueue().peek(ctx)
            path = Music.get_resource(music.id)
            source = await FFmpegOpusAudio.from_probe(path)
            voice = ctx.voice_client
            voice.play(source, after=lambda _: ctx.bot.loop.create_task(
                Player._play_next(ctx, locale, True)))
            embed = Embed(title=locale.get("Play_PlayNext"),
                          description=music.title, color=0x82e6e6)
            embed.set_thumbnail(url=Music.get_thumbnail_url(music.id))
            await ctx.send(embed=embed)

    @staticmethod
    async def leave(ctx: Context):
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect(force=True)
            MusicQueue().free(ctx)

    @staticmethod
    async def search(ctx: Context, locale: LocaleProperties,
                     query: str, page_: str = "1"):
        page = int(page_)
        hits = MusicSearcher().search(query, locale.current_locale)
        embeds = []
        title = locale.get("Search_Title").format(query)
        subtitle = locale.get("Search_Subtitle").format(len(hits), page)
        embeds.append(Embed(title=title, description=subtitle, color=0x82e6e6))
        for hit in hits[9 * (page - 1):9 * page]:
            author = hit.authors[0]
            if len(hit.authors) > 1:
                author += locale.get("Search_Else").format(len(hit.authors) - 1)
            field = locale.get("Search_Field").format(author, hit.id)
            embed = Embed(title=hit.title, description=field, color=0x82e6e6)
            embed.set_thumbnail(url=Music.get_thumbnail_url(hit.id))
            embeds.append(embed)
        await ctx.send(embeds=embeds)

    @staticmethod
    async def loop(ctx: Context, locale: LocaleProperties):
        if not MusicQueue().is_exist(ctx):
            await ctx.send(locale.get("Loop_NotExist"))
            return
        is_loop = not MusicQueue().is_loop(ctx)
        MusicQueue().loop(ctx, is_loop)
        embed = Embed(title=locale.get(f"Loop_{is_loop}"), color=0x82e6e6)
        await ctx.send(embed=embed)

    @staticmethod
    async def queue(ctx: Context, locale: LocaleProperties, page_: str = "1"):
        if not MusicQueue().is_exist(ctx):
            await ctx.send(locale.get("Queue_NotExist"))
            return
        page = int(page_)
        musics = list(map(lambda x: x, MusicQueue().all(ctx)))
        embeds = []
        title = locale.get("Queue_Title")
        subtitle = locale.get("Queue_Subtitle").format(len(musics), page)
        embeds.append(Embed(title=title, description=subtitle, color=0x82e6e6))
        for music in musics[9 * (page - 1):9 * page]:
            authors = music.authors[0]
            if len(music.authors) > 1:
                authors += locale.get("Queue_Else").format(len(authors) - 1)
            field = locale.get("Queue_Field").format(authors, music.id)
            embed = Embed(title=music.title, description=field, color=0x82e6e6)
            embed.set_thumbnail(url=Music.get_thumbnail_url(music.id))
            embeds.append(embed)
        await ctx.send(embeds=embeds)

    @staticmethod
    async def help(ctx: Context, locale: LocaleProperties):
        embed = Embed(title=locale.get("Help_Title"), color=0x82e6e6)
        descriptions = loads_json(locale.get("Help_Field"))
        for description in descriptions:
            description["value"] = "\n".join(description["value"])
            embed.add_field(**description, inline=False)
        await ctx.send(embed=embed)
