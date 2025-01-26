import json
import os
from pathlib import Path

import dotenv
import streamlit as st
from loguru import logger

from lawsy.ai.query_expander import QueryExpander
from lawsy.ai.report_writer import ReportWriter
from lawsy.encoder.me5 import ME5Instruct
from lawsy.retriever.faiss import FaissHNSWRetriever

dotenv.load_dotenv()
output_dir = Path(os.getenv("OUTPUT_DIR", Path(__file__).parent.parent.parent.parent / "outputs"))


def load_article_chunks() -> dict:
    if "article_chunks" not in st.session_state:
        with st.spinner("loading article chunks..."):
            logger.info("loading article chunks")
            result = {}
            with open(output_dir / "lawsy" / "article_chunks.jsonl") as fin:
                for line in fin:
                    d = json.loads(line)
                    key = (d["file_name"], d["anchor"])
                    result[key] = d
            st.session_state.article_chunks = result
    return st.session_state.article_chunks


def load_text_encoder() -> ME5Instruct:
    if "text_encoder" not in st.session_state:
        with st.spinner("loading text encoder..."):
            logger.info("loading text encoder...")
            st.session_state.text_encoder = ME5Instruct()
    return st.session_state.text_encoder


def load_vector_search_retriever() -> FaissHNSWRetriever:
    if "vector_search_retriever" not in st.session_state:
        with st.spinner("loading vector search retriever..."):
            logger.info("loading vector search retriever...")
            st.session_state.vector_search_retriever = FaissHNSWRetriever.load(
                output_dir / "lawsy" / "article_chunks_faiss"
            )
    return st.session_state.vector_search_retriever


def load_query_expander(_lm) -> QueryExpander:
    if "query_expander" not in st.session_state:
        with st.spinner("loading query expander..."):
            logger.info("loading query expander...")
            st.session_state.query_expander = QueryExpander(lm=_lm)
    return st.session_state.query_expander


def load_report_writer(_lm) -> ReportWriter:
    if "report_writer" not in st.session_state:
        with st.spinner("loading report writer..."):
            logger.info("loading report writer...")
            st.session_state.report_writer = ReportWriter(lm=_lm)
    return st.session_state.report_writer
