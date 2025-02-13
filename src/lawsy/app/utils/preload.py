import json
import os
from pathlib import Path

import dotenv
import streamlit as st
from loguru import logger

from lawsy.ai.mindmap_maker import MindMapMaker
from lawsy.ai.query_expander import QueryExpander
from lawsy.ai.report_writer import ReportWriter, StreamReportWriter
from lawsy.encoder.me5 import ME5Instruct
from lawsy.encoder.openai import OpenAITextEmbedding
from lawsy.retriever.article_search.faiss import FaissHNSWArticleRetriever
from lawsy.retriever.web_search.google_search import GoogleSearchWebRetriever
from lawsy.retriever.web_search.tavily_search import TavilySearchWebRetriever

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


def load_text_encoder(dim: int | None = None) -> ME5Instruct | OpenAITextEmbedding:
    if "text_encoder" not in st.session_state:
        with st.spinner("loading text encoder..."):
            logger.info("loading text encoder...")
            model_name = os.getenv("ENCODER_MODEL_NAME")
            prefix = model_name.split("/")[0] if model_name is not None else None
            if model_name is None or prefix == "openai":
                st.session_state.text_encoder = OpenAITextEmbedding(dim=dim)
            else:
                st.session_state.text_encoder = ME5Instruct()
    return st.session_state.text_encoder


def load_vector_search_article_retriever() -> FaissHNSWArticleRetriever:
    if "vector_search_article_retriever" not in st.session_state:
        with st.spinner("loading vector search article retriever..."):
            logger.info("loading vector search article retriever...")
            st.session_state.vector_search_article_retriever = FaissHNSWArticleRetriever.load(
                output_dir / "lawsy" / "article_chunks_faiss"
            )
    return st.session_state.vector_search_article_retriever


def load_google_search_web_retriever() -> GoogleSearchWebRetriever:
    if "google_search_web_retriever" not in st.session_state:
        with st.spinner("loading google search web retriever..."):
            logger.info("loading google search web retriever...")
            st.session_state.google_search_web_retriever = GoogleSearchWebRetriever()
    return st.session_state.google_search_web_retriever


def load_tavily_search_web_retriever() -> TavilySearchWebRetriever:
    if "tavily_search_web_retriever" not in st.session_state:
        with st.spinner("loading tavily search web retriever..."):
            logger.info("loading tavily search web retriever...")
            st.session_state.tavily_search_web_retriever = TavilySearchWebRetriever()
    return st.session_state.tavily_search_web_retriever


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


def load_stream_report_writer(_lm) -> StreamReportWriter:
    if "stream_report_writer" not in st.session_state:
        with st.spinner("loading stream report writer..."):
            logger.info("loading stream report writer...")
            st.session_state.stream_report_writer = StreamReportWriter(lm=_lm)
    return st.session_state.stream_report_writer


def load_mindmap_maker(_lm) -> MindMapMaker:
    if "mindmap_maker" not in st.session_state:
        with st.spinner("loading mindmap maker..."):
            logger.info("loading mindmap maker...")
            st.session_state.mindmap_maker = MindMapMaker(lm=_lm)
    return st.session_state.mindmap_maker
