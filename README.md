# discord-tag-watcher

## Setup

1. `$ git clone https://github.com/7x11x13/discord-tag-watcher && cd discord-tag-watcher`
2. Rename `data/example_config.json` to `data/config.json` and edit it to your liking (see below)
3. `$ sudo docker compose up --build -d`

## `example_config.json` with comments

```json
{
    "tag_cache_size": 20,  // How many recent tracks to store for each tag.
                           // Should be more than the number of tracks you
                           // expect to be uploaded for any given tag in
                           // the time it takes to complete a scan (including
                           // the wait time after).

    "watch_interval_s": 10,  // How many seconds to wait after each scan

    "links": [
        {
            "tags": ["electronic"], // List of tags to watch

            "webhook_url": "https://discord.com/xxxxxxxxxxxxxxx" // Webhook URL to send
                                                                 // new tracks tagged with
                                                                 // "electronic"
        },
        {
            "tags": ["UK Garage", "UKG"], // List of tags to watch

            "webhook_url": "https://discord.com/xxxxxxxxxxxxxxx" // Webhook URL to send
                                                                 // new tracks tagged with
                                                                 // "UK Garage" or "UKG"
        }
    ]
}
```
