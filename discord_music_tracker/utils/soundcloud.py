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
    'tracks': base + '/users/{}/tracks',
    'following':   base + '/users/{}/followings',
    'tags':        base + '/recent-tracks/{}'
}

async def get_sc_collection(url):
    params = {
        'client_id': config.get('soundcloud_client_id')
    }
    async with aiohttp.ClientSession() as session:
        while url:
            async with session.get(url, params=params) as r:
                r.raise_for_status()
                data = await r.json()
                if not data or not 'collection' in data:
                    return
                for resource in data['collection']:
                    yield resource
                url = data['next_href']

async def get_sc_user_id(username):
    params = {
        'url': f'https://soundcloud.com/{username}',
        'client_id': config.get('soundcloud_client_id')
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(endpoints['resolve'], params=params) as r:
            r.raise_for_status()
            data = await r.json()
            if not data or 'id' not in data:
                raise ValueError('Invalid username {username}')
            db.update_sc_username(data['id'], username)
            return data['id']

async def update_following():
    for user_id, channel_ids in db.sc_following.items():
        try:
            artists = get_sc_collection(endpoints['following'].format(user_id))
        except:
            return
        async for artist in artists:
            id = artist['id']
            for channel_id in channel_ids:
                db.add_sc_artist(channel_id, id)

async def __valid_tracks(tracks, last_updated):
    async for track in tracks:
        id = track['id']
        if db.sc_artist_track_exists(id):
            # already sent this song
            # and any songs before it
            break
        date = datetime.datetime.fromisoformat(
            track['created_at'].replace('Z', '+00:00')
        )
        if date < last_updated:
            # ignore songs before the last updated time
            break
        yield track

async def update_artists(last_updated):
    all_fail = True
    for artist_id, channel_ids in db.sc_artists.items():
        try:
            tracks = get_sc_collection(endpoints['tracks'].format(artist_id))
            all_fail = False
        except:
            continue
        async for track in __valid_tracks(tracks, last_updated):
            yield track, channel_ids
    if all_fail and len(db.sc_artists) > 0:
        raise Exception('All update_artists failed')

async def update_tags(last_updated):
    all_fail = True
    for tag, channel_ids in db.sc_tags.items():
        try:
            tracks = get_sc_collection(endpoints['tags'].format(tag))
            all_fail = False
        except:
            continue
        async for track in __valid_tracks(tracks, last_updated):
            yield tag, track, channel_ids
    if all_fail and len(db.sc_tags) > 0:
        raise Exception('All update_tags failed')