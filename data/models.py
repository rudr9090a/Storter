from pydantic import BaseModel

class LoginModel(BaseModel):
    username: str
    password: str

class PasswordChangeModel(BaseModel):
    username: str
    oldpassword: str
    newpassword: str

class LikeSongModel(BaseModel):
    username: str
    songid: str

class AlbumModel(BaseModel):
    url: str