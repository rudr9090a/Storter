import uvicorn
import asyncio
import threading
import random
from fastapi import FastAPI, HTTPException, Request
from pathlib import Path
from starlette.responses import FileResponse
import config
from data.models import LoginModel, PasswordChangeModel, LikeSongModel, AlbumModel
from data.database_handlers import init as database_init, SessionHandler, UserAccountsManager
from data.logger import logger_init
from data.authmanager import login_manager, new_user_account
from data.musicmanager import list_songs, UserMusicProfileManager, validate_music_input, MusicManager
from data.misc import request_validator
BASE_DIR = Path(__file__).resolve().parent

storterLogger = logger_init()
storterLogger.debug("Logger initialized")
sh = SessionHandler(storterLogger)
uam = UserAccountsManager(storterLogger)
umpm = UserMusicProfileManager(storterLogger)
mm = MusicManager(storterLogger)
database_init(storterLogger)
app = FastAPI()

def download_album_in_background(url: str):
    try:
        asyncio.run(mm.download_album(url))
    except Exception:
        storterLogger.exception("Background album download failed: %s", url)



@app.post("/api/auth/login")
def login(creds: LoginModel):
    result, key, aoi = login_manager(creds,sh, uam)
    if not result:
        raise HTTPException(
            status_code=401,
            detail=f"Couldn't login - {aoi}"
        )
    return {
        "success" : result,
        "session" : key,
        "aoi" : aoi
    }

@app.post("/api/auth/logout")
def logout(request: Request):
    request_validator(request,sh)
    session_id = request.cookies.get("session")
    username = request.cookies.get("username")
    result, aoi = uam.logout(session_id,username,sh)
    return {
        "result" : result,
        "aoi" : aoi
    }

@app.post("/api/auth/change_password")
def change_password(request : Request,creds: PasswordChangeModel):
    request_validator(request,sh)
    if request.cookies.get("username") != creds.username:
        raise HTTPException(
            status_code=401,
            detail="Cookies and payload data doesnt match."
        )
    result, aoi = uam.change_password(creds)
    if not result:
        raise HTTPException(
            status_code=401,
            detail=f"Couldn't change password - {aoi}"

        )
    return {
        "result" : result,
        "aoi" : aoi
    }

@app.post("/api/auth/new_user")
def new_account(creds : LoginModel):
    result, aoi = new_user_account(creds,uam)
    if not result:
        raise HTTPException(
            status_code=500,
            detail=f"Couldn't create a new account - {aoi}"
        )
    umpm.init_user_data(creds.username)
    return {
        "result" : result,
        "aoi" : aoi
    }

@app.get("/api/dashboard")
async def dashboard(request: Request):
    request_validator(request,sh)
    return {
        "songs" : list_songs(),
    }

@app.get("/api/music/{song_id}/audio")
async def stream_audio(song_id: str,request: Request):
    request_validator(request,sh)
    songs = list_songs()
    if song_id+".mp3" not in songs:
        raise HTTPException(
            status_code=404,
            detail=f"Song with id {song_id} does not exist."
        )
    path = Path(config.DEFAULT_MUSIC_DIR) / f"{song_id}.mp3"
    return FileResponse(
        path,
        media_type="audio/mpeg",
        content_disposition_type="inline",
    )
@app.post("/api/{username}/like_song")
def like_song(username : str,model : LikeSongModel, request : Request):
    validate_music_input(username, model)
    request_validator(request,sh)
    songs = list_songs()
    if model.songid + ".mp3" not in songs:
        raise HTTPException(
            status_code=404,
            detail=f"Song with id {model.songid} does not exist."
        )
    umpm.like_song(model.username, model.songid)
    return {
        "result" : "Request successful"
    }

@app.post("/api/{username}/unlike_song")
def unlike_song(username: str, model: LikeSongModel, request: Request):
    validate_music_input(username, model)
    request_validator(request,sh)
    if model.songid + ".mp3" not in list_songs():
        raise HTTPException(status_code=404, detail="Song does not exist.")
    umpm.unlike_song(username, model.songid)
    return {"result": "Request successful"}
@app.get("/api/{username}/get_liked_songs")
def get_liked_songs(username : str,request : Request):
    request_validator(request,sh)
    song_list = umpm.get_liked_songs(username)
    return {
        "result" : "Request Successful",
        "liked_song_list" : song_list
    }
@app.post("/api/downloadalbumyt")
def download_album_from_yt(model : AlbumModel, request : Request):
    request_validator(request,sh)
    storterLogger.debug(f"Album download request from {request.cookies.get("username")} - {model.url}")
    thread = threading.Thread(
        target=download_album_in_background,
        args=(model.url,),
        name="storter-album-download",
        daemon=True,
    )
    thread.start()
    return {
        "result" : "Request successful",
        "status" : "Download started in the background"
    }
@app.get("/api/get_song_data/{songid}")
def get_song_data(songid: str, request : Request):
    request_validator(request,sh)
    songid += ".mp3"
    return mm.get_song_data(songid)
@app.get("/api/get_song_thumbnail/{filename}")
def get_song_thumbnail(filename: str, request : Request):
    request_validator(request,sh)
    path = Path(config.DEFAULT_MUSIC_DIR) / f"{filename}.png"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="png file not found")
    return FileResponse(
        path=path,
        media_type="image/png",
        content_disposition_type="inline"
    )
if __name__ == "__main__":
    storterLogger.debug("FastAPI initialized")
    storterLogger.info(f"Visit the website on http://127.0.0.1:{config.PORT}/files/login.html ")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=config.PORT,
        log_level="debug" if config.UVI_DEBUG else "critical"
    )

