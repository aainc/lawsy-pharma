import os
from pathlib import Path

import dotenv
import dspy
import streamlit as st
from loguru import logger

from lawsy.app.utils.preload import (
    load_google_search_web_retriever,
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
google_search_web_retriever = load_google_search_web_retriever()
gpt_4o = dspy.LM("openai/gpt-4o", api_key=os.environ["OPENAI_API_KEY"], max_tokens=8192, temperature=0.01, cache=False)
gpt_4o_mini = dspy.LM(
    "openai/gpt-4o-mini", api_key=os.environ["OPENAI_API_KEY"], max_tokens=8192, temperature=0.01, cache=False
)
query_expander = load_query_expander(_lm=gpt_4o_mini)
stream_report_writer = load_stream_report_writer(_lm=gpt_4o)
rrf = RRF()


def lawsy_page():
    st.title("Lawsy")
    query = st.text_input("Query", key="research_page_query_text_input")
    if query is not None:
        query = query.strip()
    go_jp = st.checkbox("go.jpに限定", value=True, key="research_page_go_jp_checkbox")
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
                # vector search
                query_vector = text_encoder.get_query_embeddings([expanded_query])[0]
                hits = vector_search_article_retriever.search(query_vector, k=20)
                run = {}
                for result in hits:
                    key = (result.law_id, result.anchor)
                    run[key] = result.score
                    key2result[key] = result
                runs.append(run)
                # google search
                if go_jp:
                    hits = google_search_web_retriever.search(expanded_query, k=10, site="go.jp")
                else:
                    hits = google_search_web_retriever.search(expanded_query, k=10)
                run = {}
                for result in hits:
                    key = result.url
                    run[key] = 0.0  # dummy score (not used)
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

            # complete
            status.update(label="complete", state="complete", expanded=False)

        # show
        report_box = st.empty()
        report_stream = stream_report_writer(query=query, topics=query_expander_result.topics, references=references)
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
