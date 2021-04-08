"""Runs a discord bot to track recently uploaded soundcloud tracks
Usage:
    sc-discord-py [--debug | --verbose]
    sc-discord-py (-h | --help)
    sc-discord-py --version
Options:
    -h --help                   Show this screen
    --version                   Show version
    --debug                     Set logging level to DEBUG
    --verbose                   Set logging level to INFO
"""

import sys, logging
import discord

from discord.ext import commands
from docopt import docopt

from discord_music_tracker import __version__, config, config_file, logger
from discord_music_tracker.utils import database

# Global variables
arguments = None

intents = discord.Intents(messages=True, guilds=True, reactions=True)
bot = commands.Bot(command_prefix='!', intent=intents)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}')

@bot.event
async def on_guild_channel_delete(channel):
    database.delete_channel(channel)

def main():
    global arguments
    arguments = docopt(__doc__, version=__version__)

    if arguments['--debug']:
        logger.setLevel(logging.DEBUG)

    if arguments['--verbose']:
        logger.setLevel(logging.INFO)

    try:
        database.init_db()
        logger.info('Database initialized')
    except Exception:
        logger.exception('Could not initialize database')
        sys.exit(1)

    # init commands
    bot.load_extension('discord_music_tracker.cogs.soundcloud')

    token = config.get('bot_token')
    bot.run(token)
    

if __name__ == '__main__':
    main()