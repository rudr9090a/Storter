import uvicorn
from fastapi import FastAPI, HTTPException
from pathlib import Path
import config
from data.models import *
from data.database import init as database_init,admin_login
from data.logger import logger_init
BASE_DIR = Path(__file__).resolve().parent

storterLogger = logger_init()
storterLogger.debug("Logger initialized")

database_init(storterLogger)
app = FastAPI()
@app.post("/api/auth/login")
def login(creds: Login):
    if creds.username == "admin":
        storterLogger.debug("Admin login detected")
        success, defaults = admin_login(creds.username, creds.password)
        if not success:
            raise HTTPException(
                status_code=401,
                detail="Incorrect username or password",
            )


if __name__ == "__main__":
    storterLogger.debug("FastAPI initialized")
    storterLogger.info(f"Visit the website on http://127.0.0.1:{config.PORT}/files/login.html ")
    uvicorn.run(
        app,
        port=config.PORT,
        log_level="debug" if config.UVI_DEBUG else "critical"
    )