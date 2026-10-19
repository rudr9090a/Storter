import json
import os
import re
from fastapi import HTTPException
import config
from data.models import LikeSongModel
from data.dlp_manager import download_album

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
class UserMusicProfileManager:
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
        self.songs = list_songs()
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
        self.songs = list_songs()
        with open("data/user_data.json","r") as f:
            data = json.load(f)
        user_data = data.get(username)
        if user_data is None:
            return False, "The user does not exist."
        return True, user_data["liked_songs"]
    def like_song(self,username,songid):
        self.songs = list_songs()
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
        self.songs = list_songs()
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
class MusicManager:
    def __init__(self,logger):
        self.logger = logger
        self.songs = list_songs()
        try:
            f = open(config.DEFAULT_MUSIC_DIR+"/dictionary.json","r")
        except FileNotFoundError:
            f = open(config.DEFAULT_MUSIC_DIR+"/dictionary.json","w")
            json.dump({},f,indent=4)
            self.logger.debug("Creating default dictionary file for song info, previous file not found")
    def register_song(self, filename, data : dict):
        with open(config.DEFAULT_MUSIC_DIR+"/dictionary.json","r") as f:
            existing_data = json.load(f)
        if filename in existing_data:
            return
        existing_data[filename] = data
        with open(config.DEFAULT_MUSIC_DIR+"/dictionary.json","w") as f:
            json.dump(existing_data,f,indent=4)
    def get_song_data(self, filename):
        with open(config.DEFAULT_MUSIC_DIR + "/dictionary.json", "r") as f:
            existing_data = json.load(f)
        try:
            return existing_data[filename]
        except KeyError:
            return {"detail":"unfinished downloaded song"}
    async def download_album(self,url):
        data = await download_album(url)
        for filename in data:
            self.register_song(filename,data[filename])
SAFE_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
SAFE_SONG_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

def validate_music_input(username: str, model: LikeSongModel):
    if not SAFE_USERNAME.fullmatch(username) or username != model.username:
        raise HTTPException(status_code=400, detail="Invalid username.")
    if not SAFE_SONG_ID.fullmatch(model.songid):
        raise HTTPException(status_code=400, detail="Invalid song id.")