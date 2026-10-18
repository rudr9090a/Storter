import json
import os
import re

from fastapi import HTTPException
import config
from data.models import LikeSongModel

'''
Supported files types-
-> mp3
Further supported filetypes may include-
-> wav
-> ogg
-> flac
'''
music_dir = config.DEFAULT_MUSIC_DIR
def list_songs():
    songs = []
    for file in os.listdir(music_dir):
        if file.endswith(".mp3") or file.endswith(".wav"):
            songs.append(file)
    return songs
class MusicManager:
    def __init__(self,logger):
        self.songs = list_songs()
        self.logger = logger
        try:
            with open("data/user_data.json","r") as f:
                pass
        except FileNotFoundError:
            with open("data/user_data.json","w") as f:
                json.dump({},f,indent=4)
            with open("data/accounts.json","r") as g:
                d = json.load(g)
            for user in d:
                self.init_user_data(user)
            self.logger.debug("User data file not found, creating default")
    def init_user_data(self,username):
        with open("data/user_data.json","r") as f:
            data = json.load(f)
        data[username] = {
            "liked_songs": [],
            "favorite_artists": [],
            "recent_songs": [],
            "search_history": [],
            "playlists":[],
            "favorite_genres":[],
        }
        with open("data/user_data.json","w") as g:
            json.dump(data,g,indent=4)
    def get_liked_songs(self,username):
        with open("data/user_data.json","r") as f:
            data = json.load(f)
        user_data = data.get(username)
        if user_data is None:
            return False, "The user does not exist."
        return True, user_data["liked_songs"]
    def like_song(self,username,songid):
        with open("data/user_data.json","r") as f:
            data = json.load(f)
        if songid in data[username]['liked_songs']:
            raise HTTPException(
                status_code=409,
                detail="The song is already in the liked list"
            )
        data[username]['liked_songs'].append(songid)
        with open("data/user_data.json","w") as f:
            json.dump(data,f,indent=4)
    def unlike_song(self, username, songid):
        with open("data/user_data.json","r") as f:
            data = json.load(f)
        if songid not in data[username]['liked_songs']:
            raise HTTPException(
                status_code=404,
                detail="The song is not present in the liked song list in the first place"
            )
        data[username]['liked_songs'].remove(songid)
        with open("data/user_data.json","w") as f:
            json.dump(data,f,indent=4)


SAFE_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SAFE_SONG_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

def validate_music_input(username: str, model: LikeSongModel):
    if not SAFE_USERNAME.fullmatch(username) or username != model.username:
        raise HTTPException(status_code=400, detail="Invalid username.")
    if not SAFE_SONG_ID.fullmatch(model.songid):
        raise HTTPException(status_code=400, detail="Invalid song id.")