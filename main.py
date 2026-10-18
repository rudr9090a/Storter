import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pathlib import Path
import config
from data.models import *
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
    return {
        "result" : result,
        "session" : key,
        "aoi" : aoi
    }
@app.post("/api/auth/logout")
def logout(request: Request):
    session_data = request.cookies.get("session")
    result, aoi = uam.logout(session_data,sh)
    return {
        "result" : result,
        "aoi" : aoi,
        "session" : session_data.split("=")
    }
@app.post("/api/auth/change_password")
def change_password(creds: PasswordChange):
    result, aoi = uam.change_password(creds)
    return {
        "result" : result,
        "aoi" : aoi
    }
@app.post("/api/auth/new_user")
def new_account(creds : LoginModel):
    result, aoi = new_user_account(creds,uam)
    return {
        "result" : result,
        "aoi" : aoi
    }
@app.get("/api/dashboard")
async def dashboard(request: Request):
    session_data = request.cookies.get("session")
    session = session_data.split("=") # session data is of the type - (session_ID)=(username)
    session_validity,aoi = sh.check_session(session[1],session[0])
    return {
        "session_validity" : session_validity,
        "session_interpretation" : session,
        "aoi" : aoi
    }

if __name__ == "__main__":
    storterLogger.debug("FastAPI initialized")
    storterLogger.info(f"Visit the website on http://127.0.0.1:{config.PORT}/files/login.html ")
    uvicorn.run(
        app,
        port=config.PORT,
        log_level="debug" if config.UVI_DEBUG else "critical"
    )

