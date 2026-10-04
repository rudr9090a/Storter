from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(
        STATIC_DIR / "favicon.png",
        media_type="image/x-icon"
    )


@app.get("/image.png")
async def image():
    return FileResponse(
        STATIC_DIR / "image.png",
        media_type="image/png"
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        port=5000,
        log_level="info"
    )