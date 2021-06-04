import discord, datetime, asyncio, glob, os
from discord.ext import commands, tasks

from discord_music_tracker import logger
import discord_music_tracker
import discord_music_tracker.utils.database as db
import discord_music_tracker.utils.soundcloud as sc

class SoundcloudCog(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.updating = False
        self.__check_update.start()
        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        self.__clean_song_dir()

    @commands.command(name='followstream')
    @commands.has_permissions(administrator=True)
    async def add_stream(self, ctx, item_type):
        if item_type not in ('reposts', 'tracks', 'all'):
            await ctx.send(f'Argument `{item_type}` not valid, must be `reposts`, `tracks`, or `all`')
            return
        try:
            db.add_sc_stream(ctx.channel.id, item_type)
            await ctx.send(f'Successfully following my stream ({item_type})')
        except Exception:
            logger.exception(f'Could not follow my stream ({item_type})')
            await ctx.send(f'Could not follow my stream ({item_type})')

    @commands.command(name='unfollowstream')
    @commands.has_permissions(administrator=True)
    async def remove_stream(self, ctx):
        try:
            db.remove_sc_stream(ctx.channel.id)
            await ctx.send('Successfully unfollowed my stream')
        except Exception:
            logger.exception('Could not unfollow my stream')
            await ctx.send('Could not unfollow my stream')

    @commands.command(name='followtag')
    @commands.has_permissions(administrator=True)
    async def add_tag(self, ctx, tag):
        try:
            db.add_sc_tag(ctx.channel.id, tag)
            await ctx.send(f'Successfully followed tag `{tag}`')
        except Exception:
            logger.exception(f'Could not follow tag `{tag}`')
            await ctx.send(f'Could not follow tag `{tag}`')

    @commands.command(name='unfollowtag')
    @commands.has_permissions(administrator=True)
    async def remove_tag(self, ctx, tag):
        try:
            db.remove_sc_tag(ctx.channel.id, tag)
            await ctx.send(f'Successfully unfollowed tag `{tag}`')
        except Exception:
            logger.exception(f'Could not follow tag `{tag}`')
            await ctx.send(f'Could not follow tag `{tag}`')
            
    def __clean_song_dir(self):
        song_dir = discord_music_tracker.data_dir
        for song in glob.glob(os.path.join(song_dir, '*.mp3')):
            os.remove(song)
        for song in glob.glob(os.path.join(song_dir, '*.m4a')):
            os.remove(song)
            
    async def __download_song(self, track, format):
        self.__clean_song_dir()
        song_dir = discord_music_tracker.data_dir
        flag = '--no-original' if format == 'm4a' else '--onlymp3'
        p = await asyncio.create_subprocess_shell(
            f"scdl -l {track['permalink_url']} {flag} --path {song_dir}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        if await p.wait() == 0:
            songs = glob.glob(os.path.join(song_dir, f'*.{format}'))
            if len(songs) != 1:
                logger.error(f'Expected one {format} file, found {len(songs)}: {songs}')
                return None
            song_file = songs[0]
            if os.fstat(song_file).st_size > discord_music_tracker.config.get('max_attachment_bytes'):
                os.remove(song_file)
                song_file = None
            return song_file
        logger.error(f'Downloading song {track["permalink_url"]} failed')
        return None

    async def __send_track_embeds(self, track, channels, from_tag=None, from_type=None):
        if len(channels) == 0:
            return
        song_file = None
        if from_type == 'tracks' and 'track' in track['type']:
            # download song with scdl and upload to discord
            # only download if size is less than 8 MB
            size_128_kbps = track['duration'] / 1000 * 128 / 8 / 1000
            size_256_kbps = size_128_kbps * 2
            if size_256_kbps <= 9:
                song_file = await self.__download_song(track, 'm4a')
            if song_file is None and size_128_kbps <= 9:
                song_file = await self.__download_song(track, 'mp3')
        embed = discord.Embed() \
            .set_author(
                name = track['user']['username'],
                url = track['user']['permalink_url'],
                icon_url = track['user']['avatar_url']) \
            .set_thumbnail(url = track['artwork_url'] or track['user']['avatar_url'])
        embed.description = track['description'][:2048] if track['description'] else ""
        embed.title = track['title'][:256]
        embed.url = track['permalink_url']
        embed.timestamp = datetime.datetime.fromisoformat(
            track['created_at'].replace('Z', '+00:00')
        )
        for channel_id in channels:
            if not db.sc_channel_track_exists(channel_id, track['id']):
                if not from_tag:
                    db.add_sc_track(channel_id, track['id'], item_type=from_type)
                else:
                    db.add_sc_track(channel_id, track['id'], tag=from_tag)
                channel = self.bot.get_channel(channel_id)
                if channel:
                    content = track['discord_message'] if 'discord_message' in track else None
                    file = discord.File(song_file) if song_file is not None else None
                    await channel.send(content=content, embed=embed, file=file)
                    if song_file is not None:
                        # delete all song files
                        self.__clean_song_dir()
                else:
                    db.delete_channel(channel_id)

    async def __update_stream(self):
        hour_before = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        async for item_type, track, channels in sc.update_stream(max(hour_before, self.start_time)):
            try:
                await self.__send_track_embeds(track, channels, from_type=item_type)
            except Exception as err:
                logger.exception(f'Could not send embed for track {track}: {err}')
            

    async def __update_tags(self):
        hour_before = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        async for tag, track, channels in sc.update_tags(max(hour_before, self.start_time)):
            try:
                await self.__send_track_embeds(track, channels, from_tag=tag)
            except Exception as err:
                logger.exception(f'Could not send embed for track {track}: {err}')

    @tasks.loop(minutes=1)
    async def __check_update(self):
        if not self.updating:
            logger.debug('Updating...')
            self.updating = True
            try:
                await self.__update_stream()
                await self.__update_tags()
            except:
                logger.exception('Exception while updating')
            finally:
                self.updating = False

    @__check_update.before_loop
    async def __before_check_update(self):
        await self.bot.wait_until_ready()
        

def setup(bot):
    bot.add_cog(SoundcloudCog(bot))