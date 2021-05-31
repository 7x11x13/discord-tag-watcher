# get new tracks for tag
# get user_id for username
# get new tracks for user_id
# get following for user_id
import sys, datetime, aiohttp

from discord_music_tracker import config, logger
import discord_music_tracker.utils.database as db

base = 'https://api-v2.soundcloud.com'

endpoints = {
    'resolve':     base + '/resolve',
    'track_info':  base + '/tracks/{}',
    'stream':      base + '/stream',
    'tags':        base + '/recent-tracks/{}'
}

async def get_sc_collection(url):
    params = {
        'client_id': config.get('soundcloud_client_id')
    }
    headers = {
        'Authorization': f"OAuth {config.get('soundcloud_auth_token')}"
    }
    async with aiohttp.ClientSession() as session:
        while url:
            async with session.get(url, params=params, headers=headers) as r:
                r.raise_for_status()
                data = await r.json()
                if not data or not 'collection' in data:
                    return
                for resource in data['collection']:
                    yield resource
                url = data['next_href']

async def __valid_tracks(tracks, last_updated, tag=None):
    logger.debug(f'getting valid tracks for tag={tag}')
    async for track in tracks:
        if tag is None:
            track_type = track['type']
            item_type = 'reposts' if 'repost' in track_type else 'tracks'
            created_at = track['created_at']
            reposted_by = track['user']['username']
            if 'playlist' in track:
                track = track['playlist']
            elif 'track' in track:
                track = track['track']
            elif 'album' in track:
                track = track['album']
            else:
                raise ValueError(f'Unknown track type for item_type: {track_type}')
            track['description'] = f'Reposted by {reposted_by}'
            track['created_at'] = created_at
            track['type'] = track_type
            date = datetime.datetime.fromisoformat(
                track['created_at'].replace('Z', '+00:00')
            )
            logger.debug(f'{track["title"]} by {track["user"]["username"]} - {date}')
        id = track['id']
        if tag is None and db.sc_stream_track_exists(id, item_type):
            # already sent this song
            # and any songs before it
            logger.debug('stream track exists')
            break
        if tag is not None and db.sc_tag_track_exists(tag, id):
            logger.debug('tag track exists')
            break

        date = datetime.datetime.fromisoformat(
            track['created_at'].replace('Z', '+00:00')
        )
        if date < last_updated:
            # ignore songs before the last updated time
            logger.debug('song already seen')
            break
        logger.debug(track['id'])
        yield track

async def update_stream(last_updated):
    tracks = get_sc_collection(endpoints['stream'])
    async for track in __valid_tracks(tracks, last_updated):
        track_type = track['type']
        if track_type in ('track-repost', 'playlist-repost', 'album-repost'):
            yield 'reposts', track, db.sc_stream['reposts']
            yield 'reposts', track, db.sc_stream['all']
        elif track_type in ('track', 'playlist', 'album'):
            yield 'tracks', track, db.sc_stream['tracks']
            yield 'tracks', track, db.sc_stream['all']

async def update_tags(last_updated):
    all_fail = True
    for tag, channel_ids in db.sc_tags.items():
        try:
            tracks = get_sc_collection(endpoints['tags'].format(tag))
            all_fail = False
        except Exception as e:
            logger.warning(f'Error while fetching tag {tag} tracks')
            logger.warning(e)
            continue
        async for track in __valid_tracks(tracks, last_updated, tag=tag):
            yield tag, track, channel_ids
    if all_fail and len(db.sc_tags) > 0:
        raise Exception('All update_tags failed')