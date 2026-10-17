import config
from data.models import LoginModel
from data.database import admin_login, user_login, SessionHandler, UserAccountsManager
def login_manager(creds: LoginModel,
                  session_handler: SessionHandler,
                  acc_manager : UserAccountsManager
                  ):
    username = creds.username
    password = creds.password
    if username == config.DEFAULT_ADMIN_USERNAME:
        return admin_login(username, password, session_handler)
    else:
        return user_login(username, password, session_handler, acc_manager)


def new_user_account(creds : LoginModel,
                     acc_manager : UserAccountsManager):
    username = creds.username
    password = creds.password
    return acc_manager.create_new_user(username, password)