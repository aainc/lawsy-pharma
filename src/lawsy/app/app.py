import os
from pathlib import Path

import dotenv
import streamlit as st

dotenv.load_dotenv()
data_dir = Path(os.getenv("DATA_DIR", Path(__file__).parent.parent.parent.parent / "data"))
output_dir = Path(os.getenv("OUTPUT_DIR", Path(__file__).parent.parent.parent.parent / "outputs"))

st.set_page_config(page_title="Lawsy", layout="wide")

lawsy_page = st.Page("_pages/lawsy.py", title="Lawsy", icon=":material/bolt:")
vector_search_page = st.Page("_pages/vector_search.py", title="Vector Search", icon=":material/search:")
exp_lawsy_with_google_search_page = st.Page(
    "_pages/exp_lawsy_with_google_search.py", title="Lawsy with Google Search", icon=":material/bolt:"
)

pg = st.navigation(
    {"Main": [lawsy_page], "Components": [vector_search_page], "Experimental": [exp_lawsy_with_google_search_page]}
)
pg.run()
