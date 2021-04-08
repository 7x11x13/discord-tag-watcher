import os, logging, sys
from configparser import ConfigParser

logging.basicConfig(level=os.environ.get('LOGLEVEL', 'WARNING'))
logger = logging.getLogger(__name__)

__version__ = 'v0.0.1'

if 'XDG_CONFIG_HOME' in os.environ:
    config_dir = os.path.join(os.environ['XDG_CONFIG_HOME'], 'discord-music-tracker')
else:
    config_dir = os.path.join(os.path.expanduser('~'), '.config', 'discord-music-tracker')

if 'XDG_DATA_HOME' in os.environ:
    data_dir = os.path.join(os.environ['XDG_DATA_HOME'], 'discord-music-tracker')
else:
    data_dir = os.path.join(os.path.expanduser('~'), '.local', 'share', 'discord-music-tracker')

database_file = os.path.join(data_dir, 'data.db')

default_config = \
    f"""[discord-music-tracker]
    bot_token =
    soundcloud_client_id = a3e059563d7fd3372b49b37f00a00bcf
    database_file = {database_file}"""

config_file = os.path.join(config_dir, 'discord-music-tracker.cfg')

if not os.path.exists(config_file):
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    with open(config_file, 'w') as f:
        f.write(default_config)

if not os.path.exists(data_dir):
    os.makedirs(data_dir)

config = ConfigParser()
config.read(config_file)
config = config['discord-music-tracker']

class Config:
    def __init__(self, items: dict):
        self._dict = items
    
    def get(self, key):
        value = self._dict.get(key)
        if not value:
            logger.error(f'{key} is not specified in {config_file}')
            sys.exit(1)
        return value

config = Config(config)