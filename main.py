import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging
import config
from datetime import datetime

# --- Setting up loggers ---

now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

storterLogger = logging.getLogger("storter")
storterLogger.setLevel(
    logging.DEBUG if config.DEBUG_MODE else logging.INFO
)

console_handler = logging.StreamHandler()
file_handler = logging.FileHandler(f"logs/{now}.log")

log_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

console_handler.setFormatter(log_formatter)
file_handler.setFormatter(log_formatter)

storterLogger.addHandler(console_handler)
storterLogger.addHandler(file_handler)

# ----------------------------

app = FastAPI()
app.mount("/", StaticFiles(directory="web_assets", html=True), name="web_assets")

storterLogger.debug("FastAPI initialized")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        port=5000,
        log_level="debug" if config.UVI_DEBUG else "critical"
    )