import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pathlib import Path
from starlette.responses import FileResponse
import config
from data.models import LoginModel, PasswordChangeModel, LikeSongModel
from data.database_handlers import init as database_init, SessionHandler, UserAccountsManager
from data.logger import logger_init
from data.authmanager import login_manager, new_user_account
from data.musicmanager import list_songs, MusicManager, validate_music_input

BASE_DIR = Path(__file__).resolve().parent

storterLogger = logger_init()
storterLogger.debug("Logger initialized")
sh = SessionHandler(storterLogger)
uam = UserAccountsManager(storterLogger)
mm = MusicManager(storterLogger)
database_init(storterLogger)
app = FastAPI()



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
    session_id = request.cookies.get("session")
    username = request.cookies.get("username")
    if username is None or session_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or malformed cookies."
        )
    result, aoi = uam.logout(session_id,username,sh)
    return {
        "result" : result,
        "aoi" : aoi
    }

@app.post("/api/auth/change_password")
def change_password(creds: PasswordChangeModel):
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
    return {
        "result" : result,
        "aoi" : aoi
    }

@app.get("/api/dashboard")
async def dashboard(request: Request):
    session = request.cookies.get("session")
    username = request.cookies.get("username")
    if session is None or username is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or malformed cookies."
        )
    session_validity,aoi = sh.check_session(username,session)
    if not session_validity:
        raise HTTPException(
            status_code=401,
            detail="Invalid session id."
        )
    return {
        "session_validity" : session_validity,
        "aoi" : aoi,
        "songs" : list_songs(),

    }

@app.get("/api/music/{song_id}/audio")
async def stream_audio(song_id: str,request: Request):
    session = request.cookies.get("session")
    username = request.cookies.get("username")
    if session is None or username is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or malformed cookies."
        )
    session_validity,aoi = sh.check_session(username,session)
    if not session_validity:
        raise HTTPException(
            status_code=401,
            detail="Invalid session id."
        )
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
    session = request.cookies.get("session")
    if session is None or username is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or malformed cookies."
        )
    session_validity,aoi = sh.check_session(username,session)
    if not session_validity:
        raise HTTPException(
            status_code=401,
            detail="Invalid session id."
        )
    songs = list_songs()
    if model.songid + ".mp3" not in songs:
        raise HTTPException(
            status_code=404,
            detail=f"Song with id {model.songid} does not exist."
        )
    mm.like_song(model.username,model.songid)
    return {
        "result" : "Request successful"
    }

@app.post("/api/{username}/unlike_song")
def unlike_song(username: str, model: LikeSongModel, request: Request):
    validate_music_input(username, model)
    session = request.cookies.get("session")
    if session is None:
        raise HTTPException(status_code=400, detail="Invalid or malformed cookies.")
    session_validity, _ = sh.check_session(username, session)
    if not session_validity:
        raise HTTPException(status_code=401, detail="Invalid session id.")
    if model.songid + ".mp3" not in list_songs():
        raise HTTPException(status_code=404, detail="Song does not exist.")
    mm.unlike_song(username, model.songid)
    return {"result": "Request successful"}
@app.get("/api/{username}/get_liked_songs")
def get_liked_songs(username : str,request : Request):
    session = request.cookies.get("session")
    if session is None or username is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or malformed cookies."
        )
    session_validity, aoi = sh.check_session(username, session)
    if not session_validity:
        raise HTTPException(
            status_code=401,
            detail="Invalid session id."
        )
    song_list = mm.get_liked_songs(username)
    return {
        "result" : "Request Successful",
        "liked_song_list" : song_list
    }
if __name__ == "__main__":
    storterLogger.debug("FastAPI initialized")
    storterLogger.info(f"Visit the website on http://127.0.0.1:{config.PORT}/files/login.html ")
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=config.PORT,
        log_level="debug" if config.UVI_DEBUG else "critical"
    )

