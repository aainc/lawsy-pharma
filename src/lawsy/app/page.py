import asyncio
import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import dotenv
import streamlit as st
from loguru import logger
from streamlit_markmap import markmap

from lawsy.ai.outline_creater import OutlineCreater
from lawsy.ai.query_expander import QueryExpander
from lawsy.ai.report_writer import (
    StreamConclusionWriter,
    StreamLeadWriter,
    StreamSectionWriter,
)
from lawsy.app.config import get_config
from lawsy.app.utils.cloud_logging import gcp_logger
from lawsy.app.utils.cookie import get_user_id
from lawsy.app.utils.history import Report
from lawsy.app.utils.lm import load_lm
from lawsy.app.utils.preload import (
    load_tavily_search_web_retriever,
    load_text_encoder,
    load_vector_search_article_retriever,
)
from lawsy.reranker.rrf import RRF

PAGES = {}


async def write_section(section_placeholder, section_writer, query: str, references: str, section_outline: str):
    # section_placeholder.write_stream()
    text = ""
    async for chunk in section_writer(query, references, section_outline):
        text += chunk
        section_placeholder.write(text)


def draw_mindmap(mindmap: str):
    return markmap(mindmap, height=400)


def create_lawsy_page(report: Report | None = None):
    def page_func():
        dotenv.load_dotenv()
        css = (Path(__file__).parent / "styles" / "style.css").read_text()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

        if report is not None:
            logger.info("reproduce previous report")
            with st.status("Reasoning Details"):
                st.write("query:")
                st.write(report.query)
                st.write("generated topics:")
                for i, topic in enumerate(report.topics, start=1):
                    st.write(f"[{i}] {topic}")
                st.write(f"found {len(report.references)} sources:")
                for i, result in enumerate(report.references, start=1):
                    st.write(f"[{i}] " + result.title)
                st.write("generated outline:")
                st.code(report.outline)
            # show
            pos = report.report_content.find("## ")
            assert pos >= 0
            title_and_lead = report.report_content[:pos]
            rest = report.report_content[pos:]
            st.write(title_and_lead)
            draw_mindmap(report.mindmap)
            st.write(rest)
            st.markdown("## References")
            for i, result in enumerate(report.references, start=1):
                st.write(f"[{i}] " + result.title)
                st.html(f'<a href="{result.url}">{result.url}</a>')
                st.code(result.snippet)
                st.write("")
            return

        assert report is None
        user_id = get_user_id()
        logger.info(f"user_id: {user_id}")
        text_encoder = load_text_encoder()
        vector_search_article_retriever = load_vector_search_article_retriever()
        tavily_search_web_retriever = load_tavily_search_web_retriever()

        gpt_4o = load_lm("openai/gpt-4o")
        # gpt_4o_mini = load_lm("openai/gpt-4o-mini")
        # gemini_pro = "vertex_ai/gemini-2.0-exp-02-05"
        # gemini_flash = "vertex_ai/gemini-2.0-flash-001"
        # gemini_flash_lite = "vertex_ai/gemini-2.0-flash-lite-preview-02-05"

        rrf = RRF()

        st.title("Lawsy" if report is None else report.title)
        query = st.text_area(
            "Your Research Topic", key="research_page_query_text_input", value="" if report is None else report.query
        )
        if query is not None:
            query = query.strip()
        clicked = st.button("Research", key="research_page_research_button")

        if query and clicked:
            logger.info("query: " + query)
            gcp_logger.log_struct({"event": "start-research", "user_id": user_id, "query": query}, severity="INFO")
            with st.status("processing", expanded=True) as status:
                runs = []
                key2result = {}
                # web search
                status.update(label="web search...")
                web_search_hits = []
                if get_config("free_web_search_enabled", True):
                    logger.info("free web search")
                    hits = tavily_search_web_retriever.search(query, k=10)
                    run = {}
                    for result in hits:
                        key = result.url
                        run[key] = result.meta["score"]
                        key2result[key] = result
                    logger.info("\n".join(["- " + result.title + " (" + str(result.url) + ")" for result in hits]))
                    runs.append(run)
                    web_search_hits.extend(hits)
                if len(get_config("web_search_domains")) > 0:
                    domains = get_config("web_search_domains")
                    logger.info("web search with domains: " + ", ".join(domains))
                    hits = tavily_search_web_retriever.search(query, k=10, domains=domains)
                    run = {}
                    for result in hits:
                        key = result.url
                        run[key] = result.meta["score"]
                        key2result[key] = result
                    logger.info("\n".join(["- " + result.title + " (" + str(result.url) + ")" for result in hits]))
                    runs.append(run)
                    web_search_hits.extend(hits)
                # query expansion
                status.update(label="query expansion...")
                query_expander = QueryExpander(lm=gpt_4o)
                web_search_results = []
                for i, result in enumerate(web_search_hits, start=1):
                    web_search_results.append(f"[{i}] {result.title}\n{result.snippet}")
                web_search_results = "\n\n".join(web_search_results)
                query_expander_result = query_expander(query=query, web_search_results=web_search_results)
                expanded_queries = [query] + query_expander_result.topics
                st.write("generated topics:")
                for i, topic in enumerate(query_expander_result.topics, start=1):
                    st.write(f"[{i}] {topic}")
                # vector search
                status.update(label="legal search..")
                for expanded_query in expanded_queries:
                    logger.info("vector search: " + expanded_query)
                    query_vector = text_encoder.get_query_embeddings([expanded_query])[0]
                    hits = vector_search_article_retriever.search(query_vector, k=10)
                    run = {}
                    for result in hits:
                        key = (result.law_id, result.anchor)
                        run[key] = result.score
                        key2result[key] = result
                    logger.info("\n".join(["- " + result.title + " (" + str(result.url) + ")" for result in hits]))
                    runs.append(run)
                # fuse
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
                    if len(seen) == 50:
                        break
                # create outline
                status.update(label="creating outline...")
                outline_creater = OutlineCreater(lm=gpt_4o)
                outline_creater_result = outline_creater(
                    query=query, topics=query_expander_result.topics, references=references
                )
                st.write("generated outline:")
                st.code(outline_creater_result.outline.to_text())
                # complete
                status.update(label="complete", state="complete", expanded=False)

            id2reference = {i: search_result for i, search_result in enumerate(search_results, start=1)}

            # show
            outline = outline_creater_result.outline
            st.write("# " + outline.title)  # title
            lead_box = st.empty()  # lead
            mindmap_box = st.empty()  # mindmap
            section_boxes = [st.empty() for _ in outline.section_outlines]  # section
            conclusion_header_box = st.empty()
            conclusion_box = st.empty()  # conclusion

            stream_lead_writer = StreamLeadWriter(lm=gpt_4o)
            lead_box.write_stream(stream_lead_writer(query=query, outline=outline.to_text()))
            lead = stream_lead_writer.lead
            with mindmap_box.container():
                mindmap = outline.to_text()
                logger.info("mindmap :\n" + mindmap)
                draw_mindmap(mindmap)
            stream_section_writers = [StreamSectionWriter(lm=gpt_4o) for _ in outline.section_outlines]
            tasks = []
            for section_box, section_outline, stream_section_writer in zip(
                section_boxes, outline.section_outlines, stream_section_writers
            ):
                ref_ids = set()
                for subsection_outline in section_outline.subsection_outlines:
                    ref_ids.update(subsection_outline.reference_ids)
                ref_ids = sorted(ref_ids)
                refs = []
                for ref_id in ref_ids:
                    ref = id2reference[ref_id]
                    refs.append(f"[{ref_id}] " + ref.title + "\n" + ref.snippet)
                refs = "\n\n".join(refs)
                tasks.append(write_section(section_box, stream_section_writer, query, refs, section_outline.to_text()))

            async def finish_section_writing():
                await asyncio.gather(*tasks)

            asyncio.run(finish_section_writing())
            conclusion_header_box.write("## 結論")
            report_draft = "\n".join(
                ["# " + outline.title, lead] + [writer.section_content for writer in stream_section_writers]
            )
            stream_conclusion_writer = StreamConclusionWriter(gpt_4o)
            conclusion_box.write_stream(stream_conclusion_writer(query, report_draft))
            conclusion = stream_conclusion_writer.conclusion
            report_content = "\n".join([report_draft, "## 結論", conclusion])

            st.write("## References")
            for i, result in enumerate(search_results, start=1):
                st.write(f"[{i}] " + result.title)
                # st.subheader(f"{i}. score: {result.score:.2f}")  # type: ignore
                st.html(f'<a href="{result.url}">{result.url}</a>')
                st.code(result.snippet)
                # 負荷がかかるので一旦避けておく
                # st.components.v1.iframe(result.url, height=500)  # type: ignore
                st.write("")

            # save
            title = outline.title
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
                outline=outline.to_text(),
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
