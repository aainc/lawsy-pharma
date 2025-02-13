from uuid import uuid4

from streamlit_cookies_controller import CookieController

cookie_controller = None


def init_cookies():
    global cookie_controller
    cookie_controller = CookieController(key="lawsy-cookie")


def get_user_id() -> str:
    assert cookie_controller is not None
    user_id = cookie_controller.get("user_id")
    if user_id is None:
        user_id = "user-" + str(uuid4())
    cookie_controller.set("user_id", user_id, max_age=365 * 86400)
    return user_id
