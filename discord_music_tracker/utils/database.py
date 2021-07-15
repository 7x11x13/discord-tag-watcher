import sqlite3, atexit, heapq, datetime

from discord_music_tracker import config, logger

# class to store temporary data in a set
class DecaySet(set):
    def __init__(self):
        self.last_added = [] # priority q with (datetime, value)
        self.values = set()

    def __contains__(self, value):
        return value in self.values

    def add(self, value):
        now = datetime.datetime.now(datetime.timezone.utc)
        heapq.heappush(self.last_added, (now, value))
        self.values.add(value)
        # remove items older than 1 hour
        while self.last_added:
            date, v = self.last_added[0]
            if date + datetime.timedelta(hours=1) > now:
                break
            self.values.discard(v)
            heapq.heappop(self.last_added)

    def discard(self, value):
        self.values.discard(value)
        
    def __repr__(self):
        return self.values.__repr__()

sc_stream_channel = dict()    # {channel_id: item_type}
sc_tags_channel = dict()      # {channel_id: set(tag)}

sc_stream = {'all': set(), 'reposts': set(), 'tracks': set()}
sc_tags = dict()      # {tag: set(channel_id)}

sc_stream_tracks = {'reposts': DecaySet(), 'tracks': DecaySet()}
sc_tag_tracks = dict()          # {tag: DecaySet(track_id)}
sc_channel_tracks = dict()      # {channel_id: DecaySet(tracks)}

sc_download_channels = set()

con = None

def init_db():
    path = config.get('database_file')
    global con
    con = sqlite3.connect(path)
    atexit.register(con.close)
    cur = con.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS sc_stream
            (channel_id integer NOT NULL UNIQUE, item_type text NOT NULL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sc_tags
        (channel_id integer NOT NULL, tag text NOT NULL, UNIQUE(channel_id, tag))''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sc_download
        (channel_id integer NOT NULL UNIQUE)''')

    con.commit()

    # load dbs into memory
    for channel_id, tag in cur.execute('SELECT * FROM sc_tags'):
        if channel_id not in sc_tags_channel:
            sc_tags_channel[channel_id] = set()
        sc_tags_channel[channel_id].add(tag)

        if tag not in sc_tags:
            sc_tags[tag] = set()
        sc_tags[tag].add(channel_id)
        
        if tag not in sc_tag_tracks:
            sc_tag_tracks[tag] = DecaySet()

    for channel_id, item_type in cur.execute('SELECT * FROM sc_stream'):
        sc_stream_channel[channel_id] = item_type
        sc_stream[item_type].add(channel_id)
        
    for row in cur.execute('SELECT * FROM sc_download'):
        channel_id = row[0]
        sc_download_channels.add(channel_id)
        

def add_sc_stream(channel_id, item_type):
    sc_stream_channel[channel_id] = item_type
    sc_stream[item_type].add(channel_id)
    cur = con.cursor()
    cur.execute('REPLACE INTO sc_stream VALUES(?,?)', (channel_id, item_type))
    con.commit()

def remove_sc_stream(channel_id):
    if channel_id in sc_stream_channel:
        del sc_stream_channel[channel_id]

    for item_type, channels in sc_stream.items():
        channels.discard(channel_id)

    cur = con.cursor()
    cur.execute('DELETE FROM sc_stream WHERE channel_id=?', (channel_id,))
    con.commit()

def add_sc_tag(channel_id, tag):
    if channel_id not in sc_tags_channel:
        sc_tags_channel[channel_id] = set()
    sc_tags_channel[channel_id].add(tag)

    if tag not in sc_tags:
        sc_tags[tag] = set()
    sc_tags[tag].add(channel_id)

    cur = con.cursor()
    cur.execute('INSERT OR IGNORE INTO sc_tags VALUES(?,?)', (channel_id, tag))
    con.commit()

def remove_sc_tag(channel_id, tag):
    if channel_id not in sc_tags_channel:
        return
    sc_tags_channel[channel_id].discard(tag)

    if tag not in sc_tags:
        sc_tags[tag] = set()
        return
    sc_tags[tag].discard(channel_id)
    if len(sc_tags[tag]) == 0:
        del sc_tags[tag]

    cur = con.cursor()
    cur.execute('DELETE FROM sc_tags WHERE channel_id=? AND tag=?', (channel_id, tag))
    con.commit()

def add_sc_stream_track(track_id, item_type):
    sc_stream_tracks[item_type].add(track_id)

def add_sc_tag_track(tag, track_id):
    if tag not in sc_tag_tracks:
        sc_tag_tracks[tag] = DecaySet()
    sc_tag_tracks[tag].add(track_id)
    logger.debug(f'add tag: {sc_tag_tracks[tag]}')

def add_sc_track(channel_id, track_id, tag=None, item_type=None):
    if tag:
        add_sc_tag_track(tag, track_id)
    else:
        add_sc_stream_track(track_id, item_type)
    if channel_id not in sc_channel_tracks:
        sc_channel_tracks[channel_id] = DecaySet()
    sc_channel_tracks[channel_id].add(track_id)

def get_all_sc_tags(channel_id):
    if not channel_id in sc_tags_channel:
        return
    yield from sc_tags_channel[channel_id]

def sc_tag_exists(channel_id, tag):
    x = sc_tags_channel.get(channel_id)
    return x is not None and tag in x

def sc_stream_track_exists(track_id, item_type):
    return track_id in sc_stream_tracks[item_type]

def sc_tag_track_exists(tag, track_id):
    x = sc_tag_tracks.get(tag)
    return x is not None and track_id in x

def sc_channel_track_exists(channel_id, track_id):
    x = sc_channel_tracks.get(channel_id)
    return x is not None and track_id in x

def toggle_dl(channel_id):
    cur = con.cursor()
    ret = None
    if channel_id in sc_download_channels:
        sc_download_channels.discard(channel_id)
        cur.execute('DELETE FROM sc_download WHERE channel_id=?', (channel_id,))
        ret = False
    else:
        sc_download_channels.add(channel_id)
        cur.execute('INSERT OR IGNORE INTO sc_download VALUES(?)', (channel_id,))
        ret = True
    con.commit()
    return ret
    
def is_download_channel(channel_id):
    return channel_id in sc_download_channels    

def delete_channel(channel):

    sc_tags_channel.pop(channel, None)
    sc_stream_channel.pop(channel, None)

    # don't update reverse tables cus it's slow

    cur = con.cursor()
    cur.execute('DELETE FROM sc_stream WHERE channel_id=?', (channel,))
    cur.execute('DELETE FROM sc_tags WHERE channel_id=?', (channel,))
    cur.execute('DELETE FROM sc_download WHERE channel_id=?', (channel,))
    con.commit()