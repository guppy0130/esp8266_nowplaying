import importlib.metadata
import os
import shutil
from base64 import b64encode
from io import BytesIO
from pathlib import Path
from typing import Annotated
from urllib.parse import urljoin

import requests
import spotipy
from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import RedirectResponse
from PIL import Image, ImageEnhance
from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyOAuth
from starlette.datastructures import URL
from typing_extensions import TypedDict

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_SCOPE = "user-read-currently-playing"
IMG_WIDTH = 64
DEFAULT_WAIT_TIME = 1000 * 3  # the server can suggest a default update time

# expose a webserver
metadata = importlib.metadata.metadata("esp8266-nowplaying").json
app = FastAPI(
    title=metadata["name"],  # type: ignore
    version=metadata["version"],  # type: ignore
    summary=metadata["summary"],  # type: ignore
)

# setup for spotipy
caches_folder = (
    Path(os.getenv("SPOTIFY_TOKEN_CACHE_DIR", "./.spotify-cache"))
    .expanduser()
    .resolve()
)
caches_folder.mkdir(parents=True, exist_ok=True)


def session_cache_path(user: str) -> Path:
    cache_file = caches_folder / user
    return cache_file


def image_fetch(url: str) -> Image.Image:
    """
    Fetches image at ``url``, returns pixel values in ``mode``
    """
    response = requests.get(url)
    image_buffer = BytesIO(response.content)
    # https://pillow.readthedocs.io/en/stable/handbook/concepts.html#modes
    return Image.open(image_buffer).convert("RGB")


def spotify_obj(user: str, base_url: URL):
    cache_handler = CacheFileHandler(cache_path=session_cache_path(user))
    auth_manager = SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=urljoin(str(base_url), "callback"),
        scope=SPOTIFY_SCOPE,
        cache_handler=cache_handler,
        state=user,
        show_dialog=True,
        open_browser=False
    )
    spotify = spotipy.Spotify(auth_manager=auth_manager)
    return spotify, auth_manager


@app.get("/")
def index():
    return "Please auth at /authorize/<your spotify username>"

@app.get("/authorize/{user}/")
def auth(
    user: str,
    request: Request,
):
    spotify, auth_manager = spotify_obj(user, base_url=request.base_url)
    if not auth_manager.validate_token(auth_manager.get_cached_token()):
        return RedirectResponse(url=auth_manager.get_authorize_url())


@app.get("/user/{user}/")
def user(
    user: str,
    request: Request,
):
    """Main endpoint. If a user has previously authed with this, it will be
    available for use"""
    # there's a max of 10-20 req/s?
    # https://stackoverflow.com/questions/30548073/spotify-web-api-rate-limits#comment75952503_30557896

    # return the artist, track, playtime remaining, and album art pixels
    track_info = get_tracks(user, request=request)
    image_bytes = _art_helper(user, request=request)

    return {**track_info, "image_bytes": b64encode(image_bytes.read())}


class TrackInfo(TypedDict):
    track_name: str
    artists: str
    remaining_time: int


@app.get("/user/{user}/track")
def get_tracks(user: str, request: Request) -> TrackInfo:
    """Get track info (name, artists, time remaining)"""
    spotify, _ = spotify_obj(user, base_url=request.base_url)
    track = spotify.current_user_playing_track()

    if track is None or track["is_playing"] is False:
        # when not playing, return no data
        return {
            "track_name": "nothing playing",
            "artists": "",
            "remaining_time": DEFAULT_WAIT_TIME,
        }

    # get some info
    artists = []
    for artist in track["item"]["artists"]:
        if artist["type"] == "artist":
            artists.append(artist["name"])
    artists = ", ".join(artists)

    track_name = track["item"]["name"]
    remaining_time: int = track["item"]["duration_ms"] - track["progress_ms"]

    return {
        "track_name": track_name,
        "artists": artists,
        "remaining_time": remaining_time,
    }


def _art_helper(user: str, request: Request) -> BytesIO:
    # parse the image returned by the api
    spotify, _ = spotify_obj(user, base_url=request.base_url)
    track = spotify.current_user_playing_track()

    data = bytearray((0, 0, 0) * (IMG_WIDTH * IMG_WIDTH))
    img = Image.frombuffer(mode="RGB", size=(64, 64), data=data)
    img_colors = 1

    if track and track["is_playing"]:
        images = track["item"]["album"]["images"]

        # figure out which image to render
        # there's usually a 64x64 image?
        for image in images:
            # pick the image with a dimension that matches
            # probably a better way to do this, like resizing the closest image
            if image["height"] == IMG_WIDTH or image["width"] == IMG_WIDTH:
                img = image_fetch(image["url"])
                # reduce brightness by 50% because LEDs are bright
                img = ImageEnhance.Brightness(image=img).enhance(0.5)
                # not too many colors, because clients don't have a lot of
                # memory.
                # TODO: make this a query param.
                img_colors=127

    img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=img_colors)
    buffer = BytesIO()
    # png offers some compression, which may help with a client's low memory.
    img.save(fp=buffer, format="png")
    buffer.seek(0)
    return buffer

@app.get(
    "/user/{user}/art",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
)
def get_art(
    user: str,
    request: Request,
) -> Response:
    """Endpoint for getting album art"""
    buffer = _art_helper(user=user, request=request)
    return Response(content=buffer.read())


@app.get("/user/{user}/logout")
def logout(user: str):
    """Logs a user out by deleting spotify auth data from the server"""
    session_cache_path(user).unlink(missing_ok=True)
    return RedirectResponse("/")


@app.get("/callback")
def callback(
    state: Annotated[str, Query()],
    code: Annotated[str, Query()],
    request: Request,
):
    """Save authorization code from user approval"""

    # trade the code for an access token and save the token to disk
    _, auth_manager = spotify_obj(user=state, base_url=request.base_url)
    if code:
        auth_manager.get_access_token(code)

    # redirect back to the main user URL
    # TODO: redirect to where the user initially tried to go to
    return RedirectResponse(app.url_path_for("user", user=state))
