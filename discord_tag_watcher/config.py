from typing import TypedDict


class ChannelConfig(TypedDict):
    tags: list[str]
    webhook_url: str


class WatcherConfig(TypedDict):
    tag_cache_size: int
    watch_interval_s: int
    links: list[ChannelConfig]
