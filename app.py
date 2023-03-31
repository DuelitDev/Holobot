# -*- coding: utf-8 -*-
# app.py

import sys
if len(sys.argv) > 1 and sys.argv[1] == "init":
    print("Please create your global configures.")
    while True:
        pass


from botlib.module import Dev, Janken, Player
from botlib.sys.config import Config
from botlib.sys.util import add_all_commands
from discord import Intents
from discord.ext.commands import Bot


bot = Bot(command_prefix="!", intents=Intents().all())


add_all_commands(bot, Dev())
add_all_commands(bot, Janken())
add_all_commands(bot, Player())


if __name__ == "__main__":
    TOKEN = Config.get("TOKEN")
    bot.run(TOKEN)
