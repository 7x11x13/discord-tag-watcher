from setuptools import setup, find_packages

import discord_music_tracker

setup(
    name='discord-music-tracker',
    version=discord_music_tracker.__version__,
    packages=find_packages(),
    author='7x11x13',
    install_requires=[
        'discord',
        'aiohttp',
        'docopt',
        'disputils'
    ],
    entry_points={
        'console_scripts': [
            'discord-music-tracker = discord_music_tracker.main:main'
        ]
    }
)