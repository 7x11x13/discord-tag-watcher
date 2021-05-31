import discord, datetime
from discord.ext import commands, tasks

from discord_music_tracker import logger
import discord_music_tracker.utils.database as db
import discord_music_tracker.utils.soundcloud as sc

class SoundcloudCog(commands.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.updating = False
        self.__check_update.start()
        self.start_time = datetime.datetime.now(datetime.timezone.utc)

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

    async def __send_track_embeds(self, track, channels, from_tag=None, from_type=None):
        if len(channels) == 0:
            return
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
                    await channel.send(embed=embed)
                else:
                    db.delete_channel(channel_id)

    async def __update_stream(self):
        hour_before = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        async for item_type, track, channels in sc.update_stream(max(hour_before, self.start_time)):
            try:
                await self.__send_track_embeds(track, channels, from_type=item_type)
            except:
                logger.exception(f'Could not send embed for track {track}')
            

    async def __update_tags(self):
        hour_before = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        async for tag, track, channels in sc.update_tags(max(hour_before, self.start_time)):
            try:
                await self.__send_track_embeds(track, channels, from_tag=tag)
            except:
                logger.exception(f'Could not send embed for track {track}')

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