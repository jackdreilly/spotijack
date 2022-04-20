from pathlib import Path
from typing import List
import streamlit as st
import sh
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


@st.experimental_singleton
def drive() -> GoogleDrive:
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)


@st.experimental_singleton
def client() -> spotipy.Spotify:
    return spotipy.Spotify(
        client_credentials_manager=SpotifyClientCredentials(**st.secrets.spotipy)
    )


@st.experimental_memo
def search(query: str, types: List[str]) -> List[dict]:
    if not query or not types:
        return {}
    return client().search(query, type=",".join(types), limit=50, market="FR")


@st.experimental_memo
def download(uri: str) -> List[str]:
    x = []
    if "album" in uri:
        for track in client().album_tracks(uri)["items"]:
            x.extend(download(track["uri"]))
        return x
    sh.Command("oggify", search_paths=[Path.cwd()])(
        sh.echo(uri), *st.secrets.spotify.values()
    )
    for f in Path(__file__).parent.glob("*.ogg"):
        mp3_name = Path(str(f).replace("ogg", "mp3"))
        if mp3_name.is_file():
            continue
        sh.ffmpeg(
            "-i",
            f.name,
            "-map_metadata",
            "0:s:0",
            "-id3v2_version",
            "3",
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "2",
            str(mp3_name),
        )
        sh.rm(f.name)
        x.append(mp3_name)
        gfile = drive().CreateFile(
            {"parents": [{"id": "1Zkh9Yew_L9NKKhJ7IwUDQ8Vs3PRMXE9o"}]}
        )
        gfile.SetContentFile(mp3_name.name)
        gfile.Upload()
        sh.rm(mp3_name.name)
    return x


for type_, value in search(
    st.text_input("Search spotify"),
    st.multiselect("Type", ["album", "track", "playlist"], ["track"]),
).items():
    st.header(type_)
    for item in value["items"]:
        c1, c2, c3, c4 = st.columns([10, 15, 3, 4])
        c1.text(",".join(artist["name"] for artist in item.get("artists", [])))
        c2.text(item["name"])
        images = item.get("images") or item.get("album", {}).get("images")
        if images:
            c3.image(images[-1]["url"])
        if c4.button("Download", key="".join(map(str, (type_, item["uri"])))):
            st.success(
                "Downloaded " + ", ".join(dl.name for dl in download(item["uri"]))
            )
