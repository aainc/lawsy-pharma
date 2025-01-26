from pathlib import Path

import streamlit as st
from loguru import logger

from lawsy.app.utils.preload import (
    load_article_chunks,
    load_text_encoder,
    load_vector_search_retriever,
)

css = (Path(__file__).parent.parent / "styles" / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def get_article_title(chunk_dict):
    title = chunk_dict["chunk"].split("\n")[0]
    article_no = chunk_dict["anchor"].split("-")[-1].split("_")[-1]
    return title + f" 第{article_no}条"


chunks = load_article_chunks()
text_encoder = load_text_encoder()
vector_search_retriever = load_vector_search_retriever()


def vector_search_page():
    st.title("Vector Search")
    query = st.text_input("Query", key="search_page_query_text_input")
    if query is not None:
        query = query.strip()
    clicked = st.button("Search", key="search_page_search_button")
    if query and clicked:
        logger.info("query: " + query)
        query_vector = text_encoder.get_query_embeddings([query])[0]
        hits = vector_search_retriever.search(query_vector, k=20)
        for i, point in enumerate(hits, start=1):
            file_name = point.meta["file_name"]  # type: ignore
            anchor = point.meta["anchor"]  # type: ignore
            law_id = file_name.split("_")[0]
            egov_url = f"https://laws.e-gov.go.jp/law/{law_id}#{anchor}"
            chunk_dict = chunks[file_name, anchor]
            article_title = get_article_title(chunk_dict)
            st.subheader(f"[{i}] " + article_title + f" (score: {point.score:.2f})")
            # st.subheader(f"{i}. score: {point.score:.2f}")  # type: ignore
            st.html(f'<a href="{egov_url}">{egov_url}</a>')
            st.markdown("```" + chunk_dict["chunk"] + "```")
            # st.components.v1.iframe(egov_url, height=500)  # type: ignore
            st.write("")


vector_search_page()
