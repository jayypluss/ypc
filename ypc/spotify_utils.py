import logging
import configparser
import os
import spotipy
import pandas as pd
from spotipy.oauth2 import SpotifyClientCredentials

logger = logging.getLogger(__name__)


def get_spotipy():
    # test if in Travis-CI
    if "TRAVIS" in os.environ and os.environ["TRAVIS"] == "true":
        try:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=os.environ["SPOTIFY_CLIENT_ID"],
                client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            )
            return spotipy.Spotify(
                client_credentials_manager=client_credentials_manager
            )
        except Exception as e:
            logger.error(e)
    else:
        # Spotify config file parsing
        user_config_dir = os.path.expanduser("~/.config/ypc/")
        try:
            config = configparser.ConfigParser()
            config.read(user_config_dir + "config.ini")
            spotify_id = config["spotify"]["id"]
            secret = config["spotify"]["secret"]
        except Exception as e:
            logger.error(
                "Error with the config file. Be sure to have a valid ~/.config/ypc/config.ini file if you want to use the spotify playlist extraction features. Error : %s",
                e,
            )
            if not os.path.exists(user_config_dir):
                logger.info(
                    "Configuration folder not found. Creating ~/.config/ypc/."
                )
                os.makedirs(user_config_dir)
            if not os.path.isfile(user_config_dir + "config.ini"):
                sample_config = (
                    "[spotify]\n"
                    "id=spotify_id_here\n"
                    "secret=spotify_secret_here\n"
                )
                with open(user_config_dir + "config.ini", "w") as f:
                    f.write(sample_config)
                logger.info(
                    "A sample configuration file has been created at ~/.config/ypc/config.ini. Go to https://developer.spotify.com/dashboard/login to create your own spotify application."
                )
            exit()

        # Spotify API
        client_credentials_manager = SpotifyClientCredentials(
            client_id=spotify_id, client_secret=secret
        )
        sp = spotipy.Spotify(
            client_credentials_manager=client_credentials_manager
        )
        return sp


def get_spotify_playlist_tracks(sp, username, playlist_id):
    df = pd.DataFrame()
    results = sp.user_playlist_tracks(username, playlist_id)
    tracks = results["items"]
    while results["next"]:
        results = sp.next(results)
        tracks.extend(results["items"])
    for song in tracks:
        artist = str(song["track"]["artists"][0]["name"])
        title = str(song["track"]["name"])
        df = df.append(
            {
                "title": artist + " - " + title,
                "playlist_url": playlist_id,
                "track_name": title,
                "artist": artist,
            },
            ignore_index=True,
        )
    return df


def get_spotify_album_tracks(sp, album_id):
    df = pd.DataFrame()
    results = sp.album_tracks(album_id, limit=None)
    logger.debug("Album tracks for %s : %s.", album_id, results)
    for song in results["items"]:
        artists = ",".join([x["name"] for x in song["artists"]])
        title = song["name"]
        track_number = int(song["track_number"])
        df = df.append(
            {
                "title": artists + " - " + title,
                "album_url": album_id,
                "track_name": title,
                "artist": artists,
                "track_number": track_number,
            },
            ignore_index=True,
        )
    return df


def get_spotify_songs(terms):
    sp = get_spotipy()
    df = pd.DataFrame()
    for item in terms:
        logger.debug(item)
        try:
            # item is album
            if "album" in item:
                df = pd.concat(
                    [df, get_spotify_album_tracks(sp, album_id=item)],
                    sort=False,
                )
            # item is playlist
            elif "playlist" in item:
                df = pd.concat(
                    [
                        df,
                        get_spotify_playlist_tracks(
                            sp, username=None, playlist_id=item
                        ),
                    ],
                    sort=False,
                )
            else:
                logger.warning("%s not recognized by get_spotify_songs.", item)
        except Exception as e:
            logger.error(
                "Error when requesting Spotify API. Be sure that your config.ini file is correct. Error : %s",
                e,
            )
            exit()
    return df
