import os
from pathlib import Path

import dotenv
import streamlit as st
from loguru import logger
from qdrant_client import QdrantClient

from lawsearch.encoder.me5 import ME5Instruct

dotenv.load_dotenv()
data_dir = Path(os.getenv("DATA_DIR", Path(__file__).parent.parent.parent.parent / "data"))
output_dir = Path(os.getenv("OUTPUT_DIR", Path(__file__).parent.parent.parent.parent / "outputs"))


st.set_page_config(
    page_title="Law Search",
    layout="wide",
)


css = (Path(__file__).parent / "styles" / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


@st.cache_resource()
def get_text_encoder() -> ME5Instruct:
    logger.info("loading text encoder...")
    return ME5Instruct()


@st.cache_resource()
def get_qdrant_client() -> QdrantClient:
    logger.info("loading qdrant index...")
    client = QdrantClient(path=str(output_dir / "law" / "laws.qdrant"))
    return client


text_encoder = get_text_encoder()
qdrant_client = get_qdrant_client()
collection_name = "law_collection"


def search_page():
    search_query = st.text_input("Search Query", key="search_query_text_input")
    if search_query:
        query_vector = text_encoder.get_query_embeddings([search_query])[0]
        hits = qdrant_client.search(
            collection_name="law_collection",
            query_vector=query_vector,
            limit=10,
        )
        shown_law_ids = set()
        for i, point in enumerate(hits):
            file_name = point.payload["file_name"]  # type: ignore
            law_id = file_name.split("_")[0]
            if law_id in shown_law_ids:
                continue
            shown_law_ids.add(law_id)
            egov_url = f"https://laws.e-gov.go.jp/law/{law_id}/"
            st.subheader(f"{len(shown_law_ids)}. score: {point.score:.2f}")  # type: ignore
            st.write(point.payload["file_name"])  # type: ignore
            st.components.v1.iframe(egov_url, height=500)  # type: ignore
            st.write("")


search_page()
