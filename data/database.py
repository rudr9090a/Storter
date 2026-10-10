import json
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
def init(logger):
    try:
        with open("data/root_acc.json", "r") as f:
            logger.debug("Admin file found")
            pass
    except FileNotFoundError:
        h = PasswordHasher().hash("root")
        default_creds = {
            "username": "admin",
            "password": h
        }
        logger.debug("Admin file not found, username and hashed password has been generated")
        with open("data/root_acc.json", "w") as f:
            json.dump(default_creds, f, indent=4)


def admin_login(username, password):
    """
    Used for authenticating an administrator and checking for default credentials.

    Args:
        username (str): The administrator's username.
        password (str): The administrator's password.

    Returns:
        tuple[bool, bool]: A tuple containing:
            - login_successful: Whether login succeeded.
            - defaults_detected: Whether default credentials were detected.a
    """
    ph = PasswordHasher()

    with open("data/root_acc.json", "r") as f:
        data = json.load(f)

    if data.get("username") != username:
        return False, None

    try:
        ph.verify(data["password"], password)
    except (VerifyMismatchError, VerificationError, ValueError, KeyError):
        return False, None

    defaults_detected = (password == "root")

    return True, defaults_detected
