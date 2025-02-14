import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import dotenv
import streamlit as st
from loguru import logger
from streamlit_markmap import markmap

from lawsy.app.utils.cloud_logging import gcp_logger
from lawsy.app.utils.cookie import get_user_id
from lawsy.app.utils.history import Report
from lawsy.app.utils.lm import load_lm
from lawsy.app.utils.preload import (
    # load_mindmap_maker,
    load_outline_creater,
    load_query_expander,
    load_stream_report_writer,
    load_tavily_search_web_retriever,
    load_text_encoder,
    load_vector_search_article_retriever,
)
from lawsy.reranker.rrf import RRF

PAGES = {}


def create_lawsy_page(report: Report | None = None):
    def page_func():
        dotenv.load_dotenv()
        css = (Path(__file__).parent / "styles" / "style.css").read_text()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

        user_id = get_user_id()
        logger.info(f"user_id: {user_id}")
        text_encoder = load_text_encoder()
        vector_search_article_retriever = load_vector_search_article_retriever()
        tavily_search_web_retriever = load_tavily_search_web_retriever()

        gpt_4o = "openai/gpt-4o"
        gpt_4o_mini = "openai/gpt-4o-mini"
        # gemini_pro = "vertex_ai/gemini-2.0-exp-02-05"
        # gemini_flash = "vertex_ai/gemini-2.0-flash-001"
        # gemini_flash_lite = "vertex_ai/gemini-2.0-flash-lite-preview-02-05"

        query_expander_lm = load_lm(gpt_4o_mini)
        query_expander = load_query_expander(_lm=query_expander_lm)
        outline_creater_lm = load_lm(gpt_4o)
        outline_creater = load_outline_creater(_lm=outline_creater_lm)
        report_writer_lm = load_lm(gpt_4o_mini)
        stream_report_writer = load_stream_report_writer(_lm=report_writer_lm)
        # mindmap_maker_lm = load_lm(gpt_4o_mini)
        # mindmap_maker = load_mindmap_maker(_lm=mindmap_maker_lm)
        rrf = RRF()

        st.title("Lawsy" if report is None else report.title)
        query = st.text_input(
            "Query", key="research_page_query_text_input", value="" if report is None else report.query
        )
        if query is not None:
            query = query.strip()
        web_search_enabled = st.checkbox(
            "web searchを有効化", value=True, key="lawsy_page_web_search_enabled_checkbox"
        )
        clicked = st.button("Research", key="research_page_research_button")

        if not clicked and report is not None:
            logger.info("reproduce previous report")
            with st.status("complete"):
                st.write("generated topics:")
                for i, topic in enumerate(report.topics, start=1):
                    st.write(f"[{i}] {topic}")
                st.write(f"found {len(report.references)} sources:")
                for i, result in enumerate(report.references, start=1):
                    st.write(f"[{i}] " + result.title)
                st.write("generated outline:")
                st.write(report.outline)
            # show
            st.write(report.report_content)
            markmap(report.mindmap, height=400)
            st.markdown("## References")
            for i, result in enumerate(report.references, start=1):
                st.write(f"[{i}] " + result.title)
                st.html(f'<a href="{result.url}">{result.url}</a>')
                st.code(result.snippet)
                st.write("")
            return

        if query and clicked:
            logger.info("query: " + query)
            gcp_logger.log_struct({"event": "start-research", "user_id": user_id, "query": query}, severity="INFO")
            with st.status("processing", expanded=True) as status:
                # query expansion
                status.update(label="query expansion...")
                query_expander_result = query_expander(query=query)
                expanded_queries = [query] + query_expander_result.topics
                st.write("generated topics:")
                for i, topic in enumerate(query_expander_result.topics, start=1):
                    st.write(f"[{i}] {topic}")
                # search
                status.update(label="seaching...")
                runs = []
                key2result = {}
                # vector search
                for expanded_query in expanded_queries:
                    query_vector = text_encoder.get_query_embeddings([expanded_query])[0]
                    hits = vector_search_article_retriever.search(query_vector, k=10)
                    run = {}
                    for result in hits:
                        key = (result.law_id, result.anchor)
                        run[key] = result.score
                        key2result[key] = result
                    runs.append(run)
                # web search for query
                if web_search_enabled:
                    hits = tavily_search_web_retriever.search(query, k=10, site="go.jp")
                    run = {}
                    for result in hits:
                        key = result.url
                        run[key] = result.meta["score"]
                        key2result[key] = result
                    runs.append(run)
                fused_ranks = rrf(runs)
                search_results = []
                for key, _ in sorted(fused_ranks.items(), key=lambda item: item[1])[::-1]:
                    result = key2result[key]
                    search_results.append(result)
                st.write(f"found {len(search_results)} sources:")
                for i, result in enumerate(search_results, start=1):
                    st.write(f"[{i}] " + result.title)
                # prepare report
                status.update(label="writing report...")
                references = []
                seen = set()
                for i, result in enumerate(search_results, start=1):
                    if result.source_type == "article":
                        if (result.rev_id, result.anchor) in seen:
                            continue
                        chunk_after_title = "\n".join(result.snippet.split("\n")[1:])
                        references.append(f"[{i}] {result.title}\n{chunk_after_title[:1024]}")
                        seen.add((result.rev_id, result.anchor))
                    elif result.source_type == "web":
                        if result.url in seen:
                            continue
                        references.append(f"[{i}] {result.title}\n{result.snippet}")
                        seen.add(result.url)
                    if len(seen) == 30:
                        break
                # create outline
                status.update(label="creating outline...")
                outline_creater_result = outline_creater(
                    query=query, topics=query_expander_result.topics, references=references
                )
                st.write("generated outline:")
                st.text(outline_creater_result.outline)
                # complete
                status.update(label="complete", state="complete", expanded=False)

            # show
            report_box = st.empty()
            mindmap_box = st.empty()
            report_stream = stream_report_writer(
                query=query, outline=outline_creater_result.outline, references=references
            )
            st.markdown("## References")
            for i, result in enumerate(search_results, start=1):
                st.write(f"[{i}] " + result.title)
                # st.subheader(f"{i}. score: {result.score:.2f}")  # type: ignore
                st.html(f'<a href="{result.url}">{result.url}</a>')
                st.code(result.snippet)
                # 負荷がかかるので一旦避けておく
                # st.components.v1.iframe(result.url, height=500)  # type: ignore
                st.write("")
            report_box.write_stream(report_stream)

            # Mindmap
            mindmap = outline_creater_result.outline  # mindmap_maker(stream_report_writer.get_text())
            # logger.info("mindmap: " + mindmap.mindmap)
            with mindmap_box.container():
                markmap(mindmap, height=400)

            # save
            report_content = stream_report_writer.get_text()
            title = report_content.strip().split("\n")[0].lstrip("#").strip()
            now = datetime.datetime.now()
            if not title:
                jst = now.astimezone(ZoneInfo("Asia/Tokyo"))
                title = jst.strftime("%Y-%m-%d %H:%M:%S.%f")
            references = []
            new_report = Report(
                id=str(uuid4()),
                timestamp=now.timestamp(),
                query=query,
                topics=query_expander_result.topics,
                title=title,
                outline=outline_creater_result.outline,
                report_content=report_content,
                mindmap=mindmap,
                references=search_results,  # reference = search result for now
                search_results=search_results,
            )
            new_report.save(user_id=user_id)
            PAGES[new_report.id] = st.Page(
                create_lawsy_page(new_report), title=new_report.title, url_path=new_report.id
            )
            logger.info("saved report")
            gcp_logger.log_struct(
                {
                    "event": "finish-research",
                    "user_id": user_id,
                    "report": {"id": new_report.id, "title": new_report.title},
                },
                severity="INFO",
            )

            st.switch_page(page=PAGES[new_report.id])

    return page_func
