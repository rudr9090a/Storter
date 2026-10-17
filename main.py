import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pathlib import Path
import config
from data.models import *
from data.database import init as database_init, SessionHandler, UserAccountsManager
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

@app.post("/api/auth/new")
def new_account(creds : LoginModel):
    result, aoi = new_user_account(creds,uam)
    return {
        "result" : result,
        "aoi" : aoi
    }
@app.get("/api/dashboard")
async def dashboard(request: Request):
    session_data = request.cookies.get("session")
    session = session_data.split("=") # session data is of the type - (username)_(session_ID)
    session = sh.check_session(session[1],session[0])
    if not session or session.is_expired:
        raise HTTPException(status_code=401, detail="Not logged in")
    if session.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    return {"message": "Admin dashboard data"}
if __name__ == "__main__":
    storterLogger.debug("FastAPI initialized")
    storterLogger.info(f"Visit the website on http://127.0.0.1:{config.PORT}/files/login.html ")
    uvicorn.run(
        app,
        port=config.PORT,
        log_level="debug" if config.UVI_DEBUG else "critical"
    )

