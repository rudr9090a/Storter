from pydantic import BaseModel

class LoginModel(BaseModel):
    username: str
    password: str

class PasswordChange(BaseModel):
    username: str
    oldpassword: str
    newpassword: str