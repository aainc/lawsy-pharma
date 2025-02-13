import os
import time
from pathlib import Path

import dotenv
import streamlit as st
from loguru import logger

from lawsy.app.page import PAGES, create_lawsy_page
from lawsy.app.utils.cookie import get_user_id, init_cookies
from lawsy.app.utils.history import get_history

dotenv.load_dotenv()
data_dir = Path(os.getenv("DATA_DIR", Path(__file__).parent.parent.parent.parent / "data"))
output_dir = Path(os.getenv("OUTPUT_DIR", Path(__file__).parent.parent.parent.parent / "outputs"))

st.set_page_config(page_title="Lawsy", layout="wide", initial_sidebar_state="expanded")
init_cookies()
# wait until cookies are synced proposed in https://www.reddit.com/r/Streamlit/comments/1fdm1pj/persisting_session_state_data_across_browser/
time.sleep(2)

user_id = get_user_id()
logger.info(f"user_id: {user_id}")

history = get_history(user_id)
if history:
    logger.info("history:\n" + "\n".join(["- " + report.title for report in history]))
else:
    logger.info("no history")
for report in history:
    PAGES[report.id] = st.Page(create_lawsy_page(report), title=report.title, url_path=report.id)

pages = {
    "New": [st.Page(create_lawsy_page(), title="New Research", url_path="new", icon=":material/edit_square:")],
    "History": [PAGES[report.id] for report in history],
}
pg = st.navigation(pages, expanded=True)
# hack for always displaying navigation
with st.sidebar:
    st.empty()
pg.run()
