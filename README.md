# ESP8266 Now Playing

Spotify album art on a 64x64 LED matrix

## Materials

* [64x64 LED matrix panel](https://www.adafruit.com/product/5362)
* [controller, networked](https://www.adafruit.com/product/4745)

## Server

The server allows users to auth with Spotify once. It manages token
lifecycle/OAuth2, selecting the correct image and processing it for client
consumption, etc.

```sh
python3.11 -m venv .venv --prompt=.
source ./.venv/bin/activate
pip install -e .
hypercorn server:app --bind 0.0.0.0:3000 --reload --access-logfile - --log-file -
```

You should auth with `/user/<your spotify username>` first before letting the
client hit this endpoint.

Refer to `/docs` for the API docs.

## Client

Currently connects to `/user/<user>/art` for just the album art. Attach another
display for the track/artists.

You should supply the following in your `settings.toml`:

```env
CIRCUITPY_WIFI_SSID
CIRCUITPY_WIFI_PASSWORD
SERVER_URL
SPOTIFY_USERNAME
```
