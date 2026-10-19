from fastapi import Request, HTTPException
from data.database_handlers import SessionHandler


def request_validator(request : Request, sh: SessionHandler):
    session = request.cookies.get("session")
    username = request.cookies.get("username")
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
