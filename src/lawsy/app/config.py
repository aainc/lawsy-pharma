from typing import Any

import streamlit as st
from streamlit_tags import st_tags

from lawsy.app.utils.cookie import get_cookie, set_cookie


def get_config(name: str, default_value: Any = None) -> Any:
    value = st.session_state.get("config_" + name)
    if value is None:
        value = get_cookie("config_" + name)
        if value is not None:
            st.session_state["config_" + name] = value
        else:
            value = default_value
    return value


def set_config(name: str, value: Any) -> None:
    st.session_state["config_" + name] = value
    set_cookie(name, value)


def init_config():
    def _init(name: str, default_value: Any) -> None:
        set_config(name, get_config(name) or default_value)

    _init("free_web_search_enabled", True)
    _init("web_search_domains", ["go.jp", "courts.go.jp", "shugiin.go.jp", "sangiin.go.jp", "cao.go.jp"])


def create_config_page():
    # ------------
    # Web検索の設定
    # ------------
    st.subheader("Web Search")

    # ドメイン指定なしのWeb検索の有効化
    free_web_search_enabled = st.checkbox("ドメイン指定なしのWeb検索を有効にする", value=True)
    set_config("free_web_search_enabled", free_web_search_enabled)

    # ドメイン指定の検索において指定するドメイン
    values = ["go.jp", "courts.go.jp", "shugiin.go.jp", "sangiin.go.jp", "cao.go.jp"]
    web_search_domains = st_tags(values, label="ドメイン指定付きWeb検索において指定するドメイン一覧")
    set_config("web_search_domains", web_search_domains)
