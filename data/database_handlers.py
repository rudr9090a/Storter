import json
import secrets
from math import floor
from time import time
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
import config
from data.models import PasswordChangeModel


def init(logger):
    try:
        with open("data/root_acc.json", "r") as f:
            logger.debug("Admin file found")
            pass
    except FileNotFoundError:
        h = PasswordHasher().hash(config.DEFAULT_ADMIN_PASSWORD)
        default_creds = {
            "username": config.DEFAULT_ADMIN_USERNAME,
            "password": h
        }
        logger.debug("Admin file not found, username and hashed password has been generated")
        with open("data/root_acc.json", "w") as f:
            json.dump(default_creds, f, indent=4)

class SessionHandler():
    def __init__(self,logger):
        f = open("data/sessions.json", "w")
        json.dump({},f,indent=4)
        f.close()
        self.logger = logger
    def create_new_session(self,username):
        session_key = secrets.token_urlsafe(32)
        with open("data/sessions.json", "r") as f:
            data = json.load(f)
        data[username] = [session_key,floor(time())]
        with open("data/sessions.json", "w") as f:
            json.dump(data, f, indent=4)
        return session_key
    def check_session(self,username,key):
        with open("data/sessions.json", "r") as f:
            data = json.load(f)
        stored_key = data.get(username)
        if stored_key is None:
            return False, "Session key is either invalid or expired"
        if key != stored_key[0]:
            return False, "Session key is invalid"
        return True, "Session key is valid"
    def delete_session(self, username):
        with open("data/sessions.json", "r") as f:
            data = json.load(f)
        if username in data:
            del data[username]
            with open("data/sessions.json", "w") as f:
                json.dump(data, f, indent=4)

class UserAccountsManager:
    def __init__(self,logger):
        self.logger = logger
        try:
            with open("data/accounts.json", "r") as f:
                logger.debug("Accounts file found")
        except FileNotFoundError:
            logger.debug("Accounts file not found, creating blank account file")
            h = PasswordHasher().hash(config.DEFAULT_PASSWORD)
            default_creds = {
                config.DEFAULT_USERNAME : h,
            }
            with open("data/accounts.json", "w") as f:
                json.dump(default_creds, f, indent=4)
    def verify(self,username,password):
        with open("data/accounts.json","r") as f:
            accounts = json.load(f)
        password_hashed = accounts.get(username)
        if password_hashed is None:
            return False, "Account associated with the following username does not exist"
        try:
            PasswordHasher().verify(password_hashed, password)
        except (VerifyMismatchError, VerificationError, ValueError, KeyError):
            return False, "Couldn't verify password, password was incorrect or hash was tampered."
        return True, None
    def create_new_user(self,username,password):
        with open("data/accounts.json","r") as f:
            accounts = json.load(f)
        if username in accounts:
            return False, "Account associated with the following username already exists"
        hash = PasswordHasher().hash(password)
        accounts[username] = hash
        with open("data/accounts.json","w") as f:
            json.dump(accounts, f, indent=4)
        return True, "Account successfully created"

    def user_login(self, username, password, session_handler : SessionHandler):
        status, reason = self.verify(username, password)
        if not status:
            return status, None , reason
        session_key = session_handler.create_new_session(username)
        session_key = session_key + "=" + username
        return status, session_key, reason

    def change_password(self, creds : PasswordChangeModel):
        old_pass_valid, _  = self.verify(creds.username,creds.oldpassword)
        if not old_pass_valid:
            return False, "Old password invalid"
        with open("data/accounts.json","r") as f:
            data = json.load(f)
        h = PasswordHasher().hash(creds.newpassword)
        data[creds.username] = h
        with open("data/accounts.json","w") as f:
            json.dump(data, f, indent=4)
        return True, "Password changed successfully"

    def logout(self, session_id, username, sh : SessionHandler):
        validity, _ = sh.check_session(username, session_id)
        if not validity:
            return validity, _
        sh.delete_session(username)
        return True, "Logout successful"


def admin_login(username, password, session_handler : SessionHandler):
    ph = PasswordHasher()
    with open("data/root_acc.json", "r") as f:
        data = json.load(f)
    if data.get("username") != username:
        return False, None, None
    try:
        ph.verify(data["password"], password)
    except (VerifyMismatchError, VerificationError, ValueError, KeyError):
        return False, None, None
    session_key = session_handler.create_new_session(username)
    session_key = session_key + "=" + username
    return True, session_key, False