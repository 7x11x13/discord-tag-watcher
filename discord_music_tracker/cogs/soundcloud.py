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

    @commands.command(name='track')
    @commands.has_permissions(administrator=True)
    async def add_following(self, ctx, username):
        try:
            user_id = await sc.get_sc_user_id(username)
            db.add_sc_following(ctx.channel.id, user_id)
            await ctx.send(f'Successfully tracking `{username}`')
        except:
            logger.info(f'Could not track user "{username}"')
            await ctx.send(f'Could not track `{username}`')

    @commands.command(name='untrack')
    @commands.has_permissions(administrator=True)
    async def remove_following(self, ctx, username):
        try:
            user_id = await sc.get_sc_user_id(username)
            db.remove_sc_following(ctx.channel.id, user_id)
            await ctx.send(f'Successfully stopped tracking `{username}`')
        except:
            logger.info(f'Could not stop tracking user "{username}"')
            await ctx.send(f'Could not stop tracking user `{username}`')

    @commands.command(name='follow')
    @commands.has_permissions(administrator=True)
    async def add_artist(self, ctx, username):
        try:
            user_id = await sc.get_sc_user_id(username)
            db.add_sc_artist(ctx.channel.id, user_id)
            await ctx.send(f'Successfully followed `{username}`')
        except:
            logger.info(f'Could not follow user "{username}"')
            await ctx.send(f'Could not follow `{username}`')

    @commands.command(name='unfollow')
    @commands.has_permissions(administrator=True)
    async def remove_artist(self, ctx, username):
        try:
            user_id = await sc.get_sc_user_id(username)
            db.remove_sc_artist(ctx.channel.id, user_id)
            await ctx.send(f'Successfully unfollowed `{username}`')
        except:
            logger.info(f'Could not unfollow user "{username}"')
            await ctx.send(f'Could not unfollow `{username}`')

    @commands.command(name='followtag')
    @commands.has_permissions(administrator=True)
    async def add_tag(self, ctx, tag):
        try:
            db.add_sc_tag(ctx.channel.id, tag)
            await ctx.send(f'Successfully followed tag `{tag}`')
        except:
            logger.info(f'Could not follow tag "{tag}"')
            await ctx.send(f'Could not follow tag `{tag}`')

    @commands.command(name='unfollowtag')
    @commands.has_permissions(administrator=True)
    async def remove_tag(self, ctx, tag):
        try:
            db.remove_sc_tag(ctx.channel.id, tag)
            await ctx.send(f'Successfully unfollowed tag `{tag}`')
        except:
            logger.info(f'Could not follow tag "{tag}"')
            await ctx.send(f'Could not follow tag `{tag}`')

    @commands.command(name='listtracking')
    async def list_tracking(self, ctx):
        for username in db.get_all_sc_following(ctx.channel.id):
            await ctx.send(f'https://soundcloud.com/{username}')

    @commands.command(name='listfollowing')
    async def list_artists(self, ctx):
        for username in db.get_all_sc_artists(ctx.channel.id):
            await ctx.send(f'https://soundcloud.com/{username}')

    @commands.command(name='listtags')
    async def list_tags(self, ctx):
        for tag in db.get_all_sc_tags(ctx.channel.id):
            await ctx.send(f'`{tag}`')

    async def __send_track_embeds(self, track, channels, from_tag=None):
        if len(channels) == 0:
            return
        embed = discord.Embed() \
            .set_author(
                name = track['user']['username'],
                url = track['user']['permalink_url'],
                icon_url = track['user']['avatar_url']) \
            .set_thumbnail(url = track['artwork_url'] or track['user']['avatar_url'])
        embed.description = track['description'][:2048]
        embed.title = track['title'][:256]
        embed.url = track['permalink_url']
        embed.timestamp = datetime.datetime.fromisoformat(
            track['created_at'].replace('Z', '+00:00')
        )
        if not from_tag:
            db.add_sc_artist_track(track['id'])
        else:
            db.add_sc_tag_track(from_tag, track['id'])
        for channel_id in channels:
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed)
            else:
                db.delete_channel(channel_id)

    async def __update_following(self):
        await sc.update_following()

    async def __update_artists(self):
        hour_before = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        async for track, channels in sc.update_artists(hour_before):
            try:
                await self.__send_track_embeds(track, channels)
            except Exception as e:
                logger.info(f'Could not send embed for track {track}')
                logger.info(e)
            

    async def __update_tags(self):
        hour_before = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        async for tag, track, channels in sc.update_tags(hour_before):
            try:
                await self.__send_track_embeds(track, channels, tag)
            except Exception as e:
                logger.info(f'Could not send embed for track {track}')
                logger.info(e)

    @tasks.loop(minutes=1)
    async def __check_update(self):
        if not self.updating:
            self.updating = True
            try:
                await self.__update_following()
                await self.__update_artists()
                await self.__update_tags()
            except:
                logger.exception('Exception while updating')
            finally:
                self.updating = False

    @__check_update.before_loop
    async def wait_for_ready(self):
        await self.bot.wait_until_ready()

    #reload sql db every 24 hours


def setup(bot):
    bot.add_cog(SoundcloudCog(bot))