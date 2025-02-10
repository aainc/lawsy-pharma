from pathlib import Path

import streamlit as st
from loguru import logger

from lawsy.app.utils.preload import (
    load_text_encoder,
    load_vector_search_article_retriever,
)

css = (Path(__file__).parent.parent / "styles" / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


text_encoder = load_text_encoder()
vector_search_article_retriever = load_vector_search_article_retriever()


def vector_search_page():
    st.title("Vector Search")
    query = st.text_input("Query", key="search_page_query_text_input")
    if query is not None:
        query = query.strip()
    clicked = st.button("Search", key="search_page_search_button")
    if query and clicked:
        logger.info("query: " + query)
        query_vector = text_encoder.get_query_embeddings([query])[0]
        hits = vector_search_article_retriever.search(query_vector, k=20)
        for i, result in enumerate(hits, start=1):
            st.subheader(f"[{i}] " + result.title + f" (score: {result.score:.2f})")
            # st.subheader(f"{i}. score: {result.score:.2f}")  # type: ignore
            st.html(f'<a href="{result.url}">{result.url}</a>')
            st.markdown("```" + result.snippet + "```")
            # st.components.v1.iframe(result.url, height=500)  # type: ignore
            st.write("")


vector_search_page()
