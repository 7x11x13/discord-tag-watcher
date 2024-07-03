from typing import TypedDict


class ChannelConfig(TypedDict):
    tags: list[str]
    webhook_url: str


class WatcherConfig(TypedDict):
    cache_size: int
    max_tag_tracks: int
    watch_interval_s: int
    links: list[ChannelConfig]
