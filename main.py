import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pathlib import Path
import config
from data.models import LoginModel, PasswordChangeModel
from data.database_handlers import init as database_init, SessionHandler, UserAccountsManager
from data.logger import logger_init
from data.authmanager import login_manager, new_user_account

BASE_DIR = Path(__file__).resolve().parent

storterLogger = logger_init()
storterLogger.debug("Logger initialized")
sh = SessionHandler(storterLogger)
uam = UserAccountsManager(storterLogger)
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
        "aoi" : aoi
        #dashboard data for that user
    }

if __name__ == "__main__":
    storterLogger.debug("FastAPI initialized")
    storterLogger.info(f"Visit the website on http://127.0.0.1:{config.PORT}/files/login.html ")
    uvicorn.run(
        app,
        port=config.PORT,
        log_level="debug" if config.UVI_DEBUG else "critical"
    )

