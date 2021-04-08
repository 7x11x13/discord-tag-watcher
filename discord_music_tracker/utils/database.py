import sqlite3
import atexit

from discord_music_tracker import config, logger

sc_following_channel = dict() # {channel_id: set(user_id)}
sc_artists_channel = dict()   # {channel_id: set(user_id)}
sc_tags_channel = dict()      # {channel_id: set(tag)}

sc_following = dict() # {user_id: set(channel_id)}
sc_artists = dict()   # {artist_id: set(channel_id)}
sc_tags = dict()      # {tag: set(channel_id)}

sc_artist_tracks = set() # set(track_id)
sc_tag_tracks = dict()   # {tag: set(track_id)}

sc_usernames = dict() # {user_id: username}

con = None

channel_tables = {
    'sc_following': sc_following_channel,
    'sc_artists': sc_artists_channel,
    'sc_tags': sc_tags_channel
}

tables = {
    'sc_following': sc_following,
    'sc_artists': sc_artists,
    'sc_tags': sc_tags
}

def init_db():
    path = config.get('database_file')
    global con
    con = sqlite3.connect(path)
    atexit.register(con.close)
    cur = con.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS sc_following
            (channel_id integer NOT NULL, id integer NOT NULL, UNIQUE(channel_id, id))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sc_artists
            (channel_id integer NOT NULL, id integer NOT NULL, UNIQUE(channel_id, id))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sc_tags
        (channel_id integer NOT NULL, tag text NOT NULL, UNIQUE(channel_id, tag))''')

    cur.execute('''CREATE TABLE IF NOT EXISTS sc_artist_tracks
            (track_id integer NOT NULL UNIQUE)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sc_tag_tracks
            (tag text NOT NULL, track_id integer NOT NULL, UNIQUE(tag, track_id))''')

    cur.execute('''CREATE TABLE IF NOT EXISTS sc_usernames
            (id integer NOT NULL UNIQUE, username text NOT NULL)''')

    con.commit()

    # load dbs into memory for faster operations
    for name, table in channel_tables.items():
        for channel_id, value in cur.execute(f'SELECT * FROM {name}'):
            if channel_id not in table:
                table[channel_id] = set()
            table[channel_id].add(value)

            reverse_table = tables[name]
            if value not in reverse_table:
                reverse_table[value] = set()
            reverse_table[value].add(channel_id)

    for track_id in cur.execute('SELECT track_id FROM sc_artist_tracks'):
        sc_artist_tracks.add(track_id)

    for tag, track_id in cur.execute('SELECT tag, track_id FROM sc_tag_tracks'):
        if tag not in sc_tag_tracks:
            sc_tag_tracks[tag] = set()
        sc_tag_tracks[tag].add(track_id)
    
    for user_id, username in cur.execute('SELECT id, username FROM sc_usernames'):
        sc_usernames[user_id] = username

def add_channel_row(table_name, channel_id, value):
    # update channel table
    channel_table = channel_tables[table_name]
    if channel_id not in channel_table:
        channel_table[channel_id] = set()
    channel_table[channel_id].add(value)

    #update reverse table if it exists
    table = tables.get(table_name)
    if table:
        if value not in table:
            table[value] = set()
        table[value].add(channel_id)

    #update sql db
    cur = con.cursor()
    cur.execute(f'INSERT OR IGNORE INTO {table_name} VALUES(?,?)', (channel_id, value))
    con.commit()

def remove_channel_row(table_name, channel_id, value, name='id'):
    #update channel table
    table = channel_tables[table_name]
    if channel_id not in table:
        return
    table[channel_id].discard(value)

    #update reverse table if it exists
    table = tables.get(table_name)
    if table:
        if value not in table:
            table[value] = set()
            return
        table[value].discard(channel_id)
        if len(table[value]) == 0:
            del table[value]

    # update sql db
    cur = con.cursor()
    cur.execute(f'DELETE FROM {table_name} WHERE channel_id=? AND {name}=?', (channel_id, value))
    con.commit()

def add_sc_following(channel_id, user_id):
    add_channel_row('sc_following', channel_id, user_id)

def remove_sc_following(channel_id, user_id):
    remove_channel_row('sc_following', channel_id, user_id)

def add_sc_artist(channel_id, user_id):
    add_channel_row('sc_artists', channel_id, user_id)

def remove_sc_artist(channel_id, user_id):
    remove_channel_row('sc_artists', channel_id, user_id)

def add_sc_artist_track(track_id):
    sc_artist_tracks.add(track_id)
    cur = con.cursor()
    cur.execute('INSERT OR IGNORE INTO sc_artist_tracks VALUES(?)', (track_id,))
    con.commit()

def add_sc_tag_track(tag, track_id):
    if tag not in sc_tag_tracks:
        sc_tag_tracks[tag] = set()
    sc_tag_tracks[tag].add(track_id)
    cur = con.cursor()
    cur.execute('INSERT OR IGNORE INTO sc_tag_tracks VALUES(?,?)', (tag, track_id))
    con.commit()
    

def add_sc_tag(channel_id, tag):
    add_channel_row('sc_tags', channel_id, tag)

def remove_sc_tag(channel_id, tag):
    remove_channel_row('sc_tags', channel_id, tag, 'tag')

def update_sc_username(user_id, username):
    sc_usernames[user_id] = username
    cur = con.cursor()
    cur.execute('''INSERT INTO sc_usernames VALUES(?,?) ON CONFLICT(id)
                   DO UPDATE SET username=excluded.username''', (user_id, username))
    con.commit()

def get_sc_username(user_id):
    return sc_usernames.get(user_id)

def get_all_sc_following(channel_id):
    if not channel_id in sc_following_channel:
        return
    for user_id in sc_following_channel[channel_id]:
        yield get_sc_username(user_id)

def get_all_sc_artists(channel_id):
    if not channel_id in sc_artists_channel:
        return
    for user_id in sc_artists_channel[channel_id]:
        yield get_sc_username(user_id)

def get_all_sc_tags(channel_id):
    if not channel_id in sc_tags_channel:
        return
    yield from sc_tags_channel[channel_id]

def sc_following_exists(channel_id, user_id):
    return user_id in sc_following_channel.get(channel_id)

def sc_artist_exists(channel_id, user_id):
    return user_id in sc_artists_channel.get(channel_id)

def sc_tag_exists(channel_id, tag):
    return tag in sc_tags_channel.get(channel_id)

def sc_artist_track_exists(track_id):
    return track_id in sc_artist_tracks

def sc_tag_track_exists(tag, track_id):
    return track_id in sc_tag_tracks.get(tag)

def delete_channel(channel):

    for table in channel_tables.values():
        table.pop(channel, None)
    
    # don't update reverse tables cus it's slow

    cur = con.cursor()
    for table_name in channel_tables:
        cur.execute(f'DELETE FROM {table_name} WHERE channel_id=?', (channel.id,))
    con.commit()