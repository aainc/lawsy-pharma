from pathlib import Path

import dotenv
import streamlit as st
from loguru import logger
from streamlit_markmap import markmap

from lawsy.app.utils.lm import load_lm
from lawsy.app.utils.preload import (
    load_mindmap_maker,
    load_outline_creater,
    load_query_expander,
    load_stream_report_writer,
    load_text_encoder,
    load_vector_search_article_retriever,
)
from lawsy.reranker.rrf import RRF

dotenv.load_dotenv()
css = (Path(__file__).parent.parent / "styles" / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

text_encoder = load_text_encoder()
vector_search_article_retriever = load_vector_search_article_retriever()

gpt_4o = "openai/gpt-4o"
gpt_4o_mini = "openai/gpt-4o-mini"
# gemini_pro = "vertex_ai/gemini-2.0-exp-02-05"
# gemini_flash = "vertex_ai/gemini-2.0-flash-001"
# gemini_flash_lite = "vertex_ai/gemini-2.0-flash-lite-preview-02-05"

query_expander_lm = load_lm(gpt_4o_mini)
query_expander = load_query_expander(_lm=query_expander_lm)
outline_creater_lm = load_lm(gpt_4o_mini)
outline_creater = load_outline_creater(_lm=outline_creater_lm)
report_writer_lm = load_lm(gpt_4o_mini)
stream_report_writer = load_stream_report_writer(_lm=report_writer_lm)
mindmap_maker_lm = load_lm(gpt_4o_mini)
mindmap_maker = load_mindmap_maker(_lm=mindmap_maker_lm)

rrf = RRF()


def lawsy_page():
    st.title("Lawsy")
    query = st.text_input("Query", key="research_page_query_text_input")
    if query is not None:
        query = query.strip()
    clicked = st.button("Research", key="research_page_research_button")
    if query and clicked:
        logger.info("query: " + query)
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
            for expanded_query in expanded_queries:
                query_vector = text_encoder.get_query_embeddings([expanded_query])[0]
                hits = vector_search_article_retriever.search(query_vector, k=10)
                run = {}
                for result in hits:
                    key = (result.law_id, result.anchor)
                    run[key] = result.score
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
                if (result.rev_id, result.anchor) in seen:
                    continue
                chunk_after_title = "\n".join(result.snippet.split("\n")[1:])
                references.append(f"[{i}] {result.title}\n{chunk_after_title[:1024]}")
                seen.add((result.rev_id, result.anchor))
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
        # Mindmap
        mindmap_box = st.empty()
        # mindmap = mindmap_maker(stream_report_writer.get_text())
        # logger.info("mindmap: " + mindmap.mindmap)
        with mindmap_box.container():
            markmap(outline_creater_result.outline, height=400)

        # Report
        report_box = st.empty()
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


lawsy_page()
