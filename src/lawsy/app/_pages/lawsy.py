import os
from pathlib import Path

import dotenv
import dspy
import streamlit as st
from loguru import logger

from lawsy.app.utils.preload import (
    load_article_chunks,
    load_query_expander,
    load_report_writer,
    load_text_encoder,
    load_vector_search_retriever,
)
from lawsy.reranker.rrf import RRF
from lawsy.retriever.point import Point

dotenv.load_dotenv()
css = (Path(__file__).parent.parent / "styles" / "style.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def get_article_title(chunk_dict):
    title = chunk_dict["chunk"].split("\n")[0]
    article_no = chunk_dict["anchor"].split("-")[-1].split("_")[-1]
    return title + f" 第{article_no}条"


chunks = load_article_chunks()
text_encoder = load_text_encoder()
vector_search_retriever = load_vector_search_retriever()
gpt_4o = dspy.LM("openai/gpt-4o", api_key=os.environ["OPENAI_API_KEY"], max_tokens=8192, temperature=0.01, cache=False)
gpt_4o_mini = dspy.LM(
    "openai/gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"], max_tokens=8192, temperature=0.01, cache=False
)
query_expander = load_query_expander(_lm=gpt_4o_mini)
report_writer = load_report_writer(_lm=gpt_4o)
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
            key2point = {}
            for expanded_query in expanded_queries:
                query_vector = text_encoder.get_query_embeddings([expanded_query])[0]
                hits = vector_search_retriever.search(query_vector, k=20)
                run = {}
                for point in hits:
                    file_name = point.meta["file_name"]  # type: ignore
                    law_id = file_name.split("_")[0]
                    anchor = point.meta["anchor"]  # type: ignore
                    key = (law_id, anchor)
                    run[key] = point.score
                    key2point[key] = point
                runs.append(run)
            fused_ranks = rrf(runs)
            search_result = []
            for key, score in sorted(fused_ranks.items(), key=lambda item: item[1])[::-1]:
                point = key2point[key]
                new_point = Point(index=point.index, score=score, meta=point.meta)
                search_result.append(new_point)
            st.write(f"found {len(search_result)} sources:")
            for i, point in enumerate(search_result, start=1):
                file_name = point.meta["file_name"]  # type: ignore
                anchor = point.meta["anchor"]  # type: ignore
                law_id = file_name.split("_")[0]
                egov_url = f"https://laws.e-gov.go.jp/law/{law_id}#{anchor}"
                chunk_dict = chunks[file_name, anchor]
                article_title = get_article_title(chunk_dict)
                st.write(f"[{i}] " + article_title)
            # generate report
            status.update(label="writing report...")
            references = []
            seen = set()
            for i, point in enumerate(search_result, start=1):
                file_name = point.meta["file_name"]  # type: ignore
                anchor = point.meta["anchor"]  # type: ignore
                law_id = file_name.split("_")[0]
                egov_url = f"https://laws.e-gov.go.jp/law/{law_id}#{anchor}"
                chunk_dict = chunks[file_name, anchor]
                if (file_name, anchor) in seen:
                    continue
                article_title = get_article_title(chunk_dict)
                chunk_after_title = "\n".join(chunk_dict["chunk"].split("\n")[1:])
                references.append(f"[{i}] {article_title}\n{chunk_after_title[:1024]}")
                seen.add((file_name, anchor))
                if len(seen) == 30:
                    break
            report_writer_result = report_writer(
                query=query, topics=query_expander_result.topics, references=references
            )
            # complete
            status.update(label="complete", state="complete", expanded=False)

        # show
        print(report_writer_result.report)
        st.markdown(report_writer_result.report)
        st.markdown("## References")
        for i, point in enumerate(search_result, start=1):
            file_name = point.meta["file_name"]  # type: ignore
            anchor = point.meta["anchor"]  # type: ignore
            law_id = file_name.split("_")[0]
            egov_url = f"https://laws.e-gov.go.jp/law/{law_id}#{anchor}"
            chunk_dict = chunks[file_name, anchor]
            article_title = get_article_title(chunk_dict)
            st.write(f"[{i}] " + article_title)
            # st.subheader(f"{i}. score: {point.score:.2f}")  # type: ignore
            st.html(f'<a href="{egov_url}">{egov_url}</a>')
            st.code(chunk_dict["chunk"])
            # 負荷がかかるので一旦避けておく
            # st.components.v1.iframe(egov_url, height=500)  # type: ignore
            st.write("")


lawsy_page()
