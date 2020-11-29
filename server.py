from flask import Flask, url_for, request, redirect, Response
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import requests
from PIL import Image
from io import BytesIO

load_dotenv()  # get vars
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_SCOPE = "user-read-currently-playing"
IMG_DIM = 64
DEFAULT_IMAGE_MODE = os.getenv("IMAGE_MODE", default=888)
DEFAULT_WAIT_TIME = 1000 * 3  # the server can suggest a default update time

# expose a webserver
app = Flask(__name__)

# setup for spotipy
caches_folder = "./.spotify-cache"
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path(user):
    return f"{caches_folder}/{user}"


def image_to_565(url):
    """Converts an image at `url` to a bytes in 565 format

    Args:
        url (str): URL to image to render

    Returns:
        list: bytes
        int: 565
    """
    try:
        response = requests.get(url)
        image = Image.open(BytesIO(response.content)).convert("RGB")
        # you'll have to list() to get the pixels themselves.
        px_list = list(image.getdata())
        hex_list = []
        for px in px_list:
            # yoinked from https://gist.github.com/hidsh/7065820
            # shift it right 2-3b to get the highest bits that we can mask
            # the highest bits = most obvious colors
            # this way, we map down from 8b color to 5-6b
            r = (px[0] >> 3) & 0b00011111
            g = (px[1] >> 2) & 0b00111111
            b = (px[2] >> 3) & 0b00011111
            # then, the value is rrrrrggggggbbbbb
            result = (r << 11) + (g << 5) + b
            # then you should split in half, because you have a short
            result_high = result >> 8 & 0b11111111
            result_low = result & 0b11111111
            hex_list.append(result_high)
            hex_list.append(result_low)
        return hex_list, 565
    except Exception:
        return [0] * (2 * IMG_DIM * IMG_DIM), 565


def image_to_888(url):
    """Converts an image at `url` to a bytes in 888 format

    Args:
        url (str): URL to image to render

    Returns:
        list: bytes
        int: 888
    """
    try:
        response = requests.get(url)
        image = Image.open(BytesIO(response.content)).convert("RGB")
        # you'll have to list() to get the pixels themselves.
        px_list = list(image.getdata())
        return [item for sublist in px_list for item in sublist], 888
    except Exception:
        return [0] * (3 * IMG_DIM * IMG_DIM), 888


def spotify_obj(user):
    auth_manager = SpotifyOAuth(
        SPOTIFY_CLIENT_ID,
        SPOTIFY_CLIENT_SECRET,
        url_for("callback", _external=True),
        scope=SPOTIFY_SCOPE,
        cache_path=session_cache_path(user),
        state=user,
        show_dialog=True,
    )
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    return spotify, auth_manager


@app.route("/")
def index():
    return "Please auth at /user/your spotify username"


# connect to the spotify api
@app.route("/user/<user>/")
def auth(user):
    """Main endpoint. If a user has previously authed with this, it will be
    available to world for use

    Args:
        user (str): User

    Returns:
        Response: the track, artist, and image_bytes with Content-Type:
        text/plain
    """
    # there's a max of 10-20 req/s?
    # https://stackoverflow.com/questions/30548073/spotify-web-api-rate-limits#comment75952503_30557896

    # get the spotify/auth_manager objects
    spotify, auth_manager = spotify_obj(user)
    # handle incoming new auths
    if request.args.get("spotify_code"):
        # pickup spotify code and set
        auth_manager.get_access_token(request.args.get("spotify_code"))

    # return the artist, track, playtime remaining, and album art pixels
    track_name, artists, remaining_time = get_tracks(user)
    # hex() doesn't pad, so return 0x{result} padded len 4
    # https://stackoverflow.com/a/52213104
    # hex_list.append(f"0x{result:04X}")
    incoming_mode = int(request.args.get("mode", default=DEFAULT_IMAGE_MODE))
    image_bytes, mode = get_album_art(user, mode=incoming_mode)
    debug = bool(request.args.get("debug", default=False))
    # how to render bytes.
    if mode == 888 or not debug:
        # if it's 888, then 0xRR, 0xGG, 0xBB
        padding = 2
    else:
        # if it's 565, then 0xRMMB where M is mixed
        # this will be what the corresponding sketch will assemble
        padding = 4
        hex_list = []
        # unsplit
        for i in range(0, len(image_bytes), 2):
            num = (image_bytes[i] << 8) + image_bytes[i + 1]
            hex_list.append(num)
        image_bytes = hex_list
    image_bytes = map(lambda result: f"0x{result:0{padding}X}", image_bytes)

    return_string = (
        f"{track_name}\n{artists}\n{remaining_time}\n{', '.join(image_bytes)}"
    )
    return Response(return_string, content_type="text/plain; charset=utf-8")


def get_tracks(user):
    """Get track info

    Args:
        user (str): User to get track info for

    Returns:
        str: track name
        str: artists, joined with ", "
        int: ms_remaining
    """
    spotify, auth_manager = spotify_obj(user)
    track = spotify.current_user_playing_track()

    if track is None or track["is_playing"] is False:
        # when not playing, return no data
        return "nothing playing", "", DEFAULT_WAIT_TIME

    # get some info
    artists = []
    for artist in track["item"]["artists"]:
        if artist["type"] == "artist":
            artists.append(artist["name"])
    artists = ", ".join(artists)

    track_name = track["item"]["name"]
    remaining_time = track["item"]["duration_ms"] - track["progress_ms"]

    return track_name, artists, remaining_time


@app.route("/user/<user>/track")
def get_tracks_endpoint(user):
    """Endpoint for getting track info

    Args:
        user (str): User to get art for

    Returns:
        Response: track_name, artists, remaining_time separated with newlines
    """
    track_name, artists, remaining_time = get_tracks(user)
    return_string = f"{track_name}\n{artists}\n{remaining_time}"
    return Response(return_string, content_type="text/plain; charset=utf-8")


def get_album_art(user, mode=DEFAULT_IMAGE_MODE):
    """Generate album art in `mode`

    Args:
        user (str): User to get art for
        mode (int, optional): 565/888. Defaults to DEFAULT_IMAGE_MODE.

    Returns:
        list: list of bytes
        int: 565/888 mode
    """
    # parse the image returned by the api
    spotify, auth_manager = spotify_obj(user)
    track = spotify.current_user_playing_track()

    multiplier = 3 if mode == 888 else 2
    if track is None or track["is_playing"] is False:
        return [0] * (IMG_DIM * IMG_DIM) * multiplier, mode

    images = track["item"]["album"]["images"]
    # figure out which image to render
    # there's usually a 64x64 image...I think
    image_to_render = None
    for image in images:
        # pick the image with a dimension that matches
        # probably a better way to do this...like resizing the closest image
        if image["height"] == IMG_DIM or image["width"] == IMG_DIM:
            image_to_render = image["url"]
    # convert the image to a set of pixels
    if mode == 565:
        return image_to_565(image_to_render)
    return image_to_888(image_to_render)


@app.route("/user/<user>/art")
def get_art_endpoint(user):
    """Endpoint for getting album art.

    Args:
        user (str): User to get art for

    Returns:
        Response: streamed pixel data?
    """
    mode = int(request.args.get("mode", default=DEFAULT_IMAGE_MODE))
    image_bytes, mode = get_album_art(user, mode)

    def generate():
        for byte in image_bytes:
            yield bytes([byte])

    return Response(
        generate(),
        mimetype="text/plain",
        headers={"Content-Length": len(image_bytes)},
    )


@app.route("/user/<user>/logout")
def logout(user):
    """Logs a user out

    Args:
        user (str): user to log out

    Returns:
        redirect: if logout successful, redirect to `/`
    """
    os.remove(session_cache_path(user))
    return redirect("/")


@app.route("/callback")
def callback():
    """Dedicated callback handler, because spotify can't

    Returns:
        redirect: redirect back to `/auth/user`
    """
    user = request.args.get("state")
    spotify_code = request.args.get("code")
    return redirect(url_for("auth", user=user, spotify_code=spotify_code))


if __name__ == "__main__":
    app.run(threaded=True, port=int(os.getenv("PORT", 5000)), host="0.0.0.0")
