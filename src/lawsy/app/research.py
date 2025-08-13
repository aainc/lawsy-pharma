import asyncio
import datetime
import os
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import dotenv
import numpy as np
import streamlit as st

from lawsy.ai.outline_creater import OutlineCreater
from lawsy.ai.query_expander import QueryExpander
from lawsy.ai.query_refiner import QueryRefiner
from lawsy.ai.report_writer import StreamConclusionWriter, StreamLeadWriter, StreamSectionWriter
from lawsy.ai.violation_summarizer import ViolationSummarizer
from lawsy.app.config import get_config
from lawsy.app.report import REPORT_PAGES, create_report_page
from lawsy.app.styles.decorate_html import (
    get_hiddenbox_ref_html,
)
from lawsy.app.templates.pharma_templates import get_template_categories, get_templates_by_category
from lawsy.app.utils.history import Report
from lawsy.app.utils.lm import load_lm
from lawsy.app.utils.mindmap import draw_mindmap
from lawsy.app.utils.preload import (
    load_text_encoder,
    load_vector_search_article_retriever,
)
from lawsy.app.utils.web_retreiver import load_web_retriever
from lawsy.utils.logging import logger


def get_logotitle_path() -> Path:
    return Path(__file__).parent / "Lawsy_logo_title_long_trans.png"


def get_logo_path() -> Path:
    return Path(__file__).parent / "Lawsy_logo_circle.png"


def construct_query_for_fusion(expanded_queries: list[str]) -> str:
    query = expanded_queries[0]
    topics = expanded_queries[1:]
    return "\n".join(
        [
            "以下の内容に関する薬機法令解説文書を作るにあたって参考になるWebページや薬機関連法令がほしい",
            "",
            "主題となるクエリー: " + query,
            "関連するトピック:",
        ]
        + ["- " + query for query in topics]
    )


async def write_section(section_placeholder, section_writer, query: str, references: str, section_outline: str):
    # section_placeholder.write_stream()
    text = ""
    async for chunk in section_writer(query, references, section_outline):
        text += chunk
        section_placeholder.write(text)


# This function is no longer needed as we're using write_stream directly
# async def write_conclusion(conclusion_placeholder, conclusion_writer, query: str, report_draft: str):
#     """結論セクションを非同期で書き込む"""
#     logger.info("Starting to write conclusion section")
#     text = "## 結論\n"
#     conclusion_placeholder.write(text)
#     chunk_count = 0
#     async for chunk in conclusion_writer(query, report_draft):
#         text += chunk
#         conclusion_placeholder.write(text)
#         chunk_count += 1
#     logger.info(f"Conclusion written with {chunk_count} chunks, total length: {len(text)}")


def create_research_page():
    dotenv.load_dotenv()
    css = (Path(__file__).parent / "styles" / "style.css").read_text()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    text_encoder = load_text_encoder()
    vector_search_article_retriever = load_vector_search_article_retriever()
    web_search_engine_name = os.getenv("LAWSY_WEB_SEARCH_ENGINE", "DuckDuckGo")
    logger.info(f"using web search engine: {web_search_engine_name}")
    web_retriever = load_web_retriever(web_search_engine_name)
    logo = get_logo_path()

    lm_name = os.getenv("LAWSY_LM", "openai/gpt-4o")
    logger.info(f"using LM: {lm_name}")
    lm = load_lm(lm_name)

    # サマリー専用LM（指定がなければ通常のLMを使用）
    summary_lm_name = os.getenv("LAWSY_VIOLATION_SUMMARY_LM", lm_name)
    if summary_lm_name != lm_name:
        summary_lm = load_lm(summary_lm_name)
        logger.info(f"using separate LM for violation summary: {summary_lm_name}")
    else:
        summary_lm = lm

    logo_col, _ = st.columns([1, 5])
    with logo_col:
        st.image(get_logotitle_path())

    with st.container():
        query_container = st.empty()
        query = query_container.chat_input(
            placeholder="薬機法について何でも聞いてください！",
            key="research_page_query_chat_input",
        )
        st.markdown(
            """
            <style>
            .custom-text-warning {
                color: grey !important;
                font-size: 12px !important;
                margin-top: -30px !important; /* 上に詰める */
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        warning_text = (
            '<p class="custom-text-warning">'
            "　 ※Lawsy Pharmaの回答は必ずしも正しいとは限りません。"
            "薬事に関する重要な情報は必ず確認するようにしてください。"
            "</p>"
        )
        st.markdown(warning_text, unsafe_allow_html=True)

    # 薬機法検索テンプレートの表示
    with st.expander("💊 薬機法検索テンプレート", expanded=False):
        st.write("よく検索される薬機関連トピックから選択できます")

        # カテゴリ選択
        categories = get_template_categories()
        selected_category = st.selectbox("カテゴリを選択", categories, index=0)

        # テンプレート選択
        templates = get_templates_by_category(selected_category)
        if templates:
            selected_template = st.selectbox("テンプレートを選択", ["選択してください"] + templates)

            if selected_template != "選択してください":
                if st.button("このテンプレートで検索", type="primary"):
                    query = selected_template
                    st.rerun()

    if not query:
        return

    messages = []
    query_container.empty()
    logger.info("query: " + query)

    ph = st.empty()
    status = st.status("推論中...", expanded=False)

    content = query
    with status:
        status.update(state="running")
        with st.chat_message("user"):
            st.write(content)
    ph.empty()
    with ph.container():
        with st.chat_message("user"):
            st.write(content)
    messages.append({"role": "user", "content": content})

    # refine query
    if len(query) >= 64:
        status.update(label="クエリーを検索向けに変換...", state="running")
        query_refiner = QueryRefiner(lm=lm)
        query_refiner_result = query_refiner(query=query)
        refined_query = query_refiner_result.refined_query
        logger.info(f"refined_query: {refined_query}")
        content = f"検索向けに変換されたクエリー:\n\n{refined_query}"
        with status:
            with st.chat_message("assistant", avatar=logo):
                st.write(content)
        ph.empty()
        with ph.container():
            with st.chat_message("assistant", avatar=logo):
                st.write(content)
        messages.append({"role": "assistant", "content": content})
    else:
        refined_query = query

    web_search_results = []

    # free web search
    if get_config("free_web_search_enabled", True):
        status.update(label="Web 検索（フリードメイン）...", state="running")
        logger.info("free web search")
        hits = web_retriever.search(refined_query, k=10)
        logger.info("\n".join(["- " + result.title + " (" + str(result.url) + ")" for result in hits]))
        web_search_results.extend(hits)
        content = "\n\n".join(
            [
                "Web 検索結果（フリードメイン）:",
                "\n".join(["- " + result.title + " (" + str(result.url) + ")" for result in hits]),
            ]
        )
        with status:
            with st.chat_message("assistant", avatar=logo):
                st.write(content)
        ph.empty()
        with ph.container():
            with st.chat_message("assistant", avatar=logo):
                st.write(content)
        messages.append({"role": "assistant", "content": content})

    # web search on specified domains
    if len(get_config("web_search_domains")) > 0:
        status.update(label="Web 検索（ドメイン指定）...", state="running")
        domains = get_config("web_search_domains")
        logger.info("web search with domains: " + ", ".join(domains))
        hits = web_retriever.search(refined_query, k=10, domains=domains)
        web_search_results.extend(hits)
        content = "\n\n".join(
            [
                "Web 検索結果（ドメイン指定）:",
                "\n".join(["- " + result.title + " (" + str(result.url) + ")" for result in hits]),
            ]
        )
        with status:
            with st.chat_message("assistant", avatar=logo):
                st.write(content)
        ph.empty()
        with ph.container():
            with st.chat_message("assistant", avatar=logo):
                st.write(content)
        messages.append({"role": "assistant", "content": content})

    # query expansion
    status.update(label="クエリー展開...", state="running")
    query_expander = QueryExpander(lm=lm)
    web_search_result_texts = []
    for i, result in enumerate(web_search_results, start=1):
        web_search_result_texts.append(f"[{i}] {result.title}\n{result.snippet}")
    web_search_results_text = "\n\n".join(web_search_result_texts)
    query_expander_result = query_expander(query=query, web_search_results=web_search_results_text)
    logger.info(
        " ".join(
            [
                "[query expansion]",
                f"(in) query: {len(query)} chars",
                f"(in) web_search_results: {len(web_search_results_text)} chars",
                f"(out) topics: {sum([len(topic) for topic in query_expander_result.topics])} chars",
            ]
        )
    )
    expanded_queries = [query] + query_expander_result.topics
    content = "\n\n".join(
        [
            "展開されたクエリー:",
            "\n\n".join([f"[{i}] {topic}" for i, topic in enumerate(query_expander_result.topics, start=1)]),
        ]
    )
    with status:
        with st.chat_message("assistant", avatar=logo):
            st.write(content)
    ph.empty()
    with ph.container():
        with st.chat_message("assistant", avatar=logo):
            st.write(content)
    messages.append({"role": "assistant", "content": content})

    # article search
    status.update(label="法令検索...", state="running")
    article_search_results = []
    query_vectors = text_encoder.get_query_embeddings(expanded_queries)
    for expanded_query, query_vector in zip(expanded_queries, query_vectors):
        logger.info("vector search: " + expanded_query)
        hits = vector_search_article_retriever.search(query_vector, k=10)
        article_search_results.extend(hits)
        logger.info("\n".join(["- " + result.title + " (" + str(result.url) + ")" for result in hits]))
        content = "\n\n".join(
            [
                "法令検索結果:",
                expanded_query,
                "\n".join(["- " + result.title + " (" + str(result.url) + ")" for result in hits]),
            ]
        )
        with status:
            with st.chat_message("assistant", avatar=logo):
                st.write(content)
        ph.empty()
        with ph.container():
            with st.chat_message("assistant", avatar=logo):
                st.write(content)
        messages.append({"role": "assistant", "content": content})
    # fusion by bi-encoder
    status.update(label="収集したナレッジのリランキング...", state="running")
    url_to_articles = {result.url: result for result in article_search_results}
    unique_article_search_results = list(url_to_articles.values())
    url_to_web_pages = {
        result.url: result for result in web_search_results if result.url not in url_to_articles
    }  # 法令もURLをもつので除外
    unique_web_search_results = list(url_to_web_pages.values())
    rich_query = construct_query_for_fusion(expanded_queries=expanded_queries)
    dim = vector_search_article_retriever.vector_dim
    rich_query_vec = text_encoder.get_query_embeddings([rich_query])[0][:dim]
    web_page_vecs = text_encoder.get_document_embeddings(
        [result.title + "\n" + result.snippet for result in unique_web_search_results]
    )[:, :dim]
    article_vecs = np.asarray(
        [vector_search_article_retriever.get_vector(result) for result in unique_article_search_results]
    )
    search_results = unique_web_search_results + unique_article_search_results
    vecs = np.vstack([web_page_vecs, article_vecs])
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    cossims = vecs.dot(rich_query_vec / np.linalg.norm(rich_query_vec))
    index = np.argsort(cossims)[::-1]
    search_results = [search_results[i] for i in index]
    content = "\n\n".join(
        [
            f"リランキングされたナレッジ（全 {len(search_results)} 件）:",
            *[f"[{i}] {result.title}" for i, result in enumerate(search_results, start=1)],
        ]
    )
    with status:
        with st.chat_message("assistant", avatar=logo):
            st.write(content)
    ph.empty()
    with ph.container():
        with st.chat_message("assistant", avatar=logo):
            st.write(content)
    messages.append({"role": "assistant", "content": content})

    # knowledge selection
    status.update(label="レポート作成に参照するナレッジの抽出...", state="running")
    references = []
    seen = set()
    total_length = 0
    for i, result in enumerate(search_results, start=1):
        if result.source_type == "article":
            if (result.rev_id, result.anchor) in seen:
                continue
            chunk_after_title = "\n".join(result.snippet.split("\n")[1:])
            reference = f"[{i}] {result.title}\n{chunk_after_title[:1024]}"
            references.append(reference)
            total_length += len(reference)
            seen.add((result.rev_id, result.anchor))
        elif result.source_type == "web":
            if result.url in seen:
                continue
            reference = f"[{i}] {result.title}\n{result.snippet}"
            references.append(reference)
            total_length += len(reference)
            seen.add(result.url)
        if len(seen) >= 200 or total_length >= 100000:  # max 128k tokens for GPT-4o
            break
    logger.info(f"effective knowledges: {len(seen)}")

    # create outline
    status.update(label="アウトラインの生成...", state="running")
    outline_creater = OutlineCreater(lm=lm)
    outline_creater_result = outline_creater(query=query, topics=query_expander_result.topics, references=references)
    content = "\n\n".join(
        [
            "生成されたアウトライン:",
            f"```{outline_creater_result.outline.to_text()}```",
        ]
    )
    with status:
        with st.chat_message("assistant", avatar=logo):
            st.write(content)
    ph.empty()
    with ph.container():
        with st.chat_message("assistant", avatar=logo):
            st.write(content)
    messages.append({"role": "assistant", "content": content})
    logger.info(
        " ".join(
            [
                "[outline_creater]",
                f"(in) query: {len(query)} chars",
                f"(in) topics: {sum([len(topic) for topic in query_expander_result.topics])} chars",
                f"(in) references: {sum([len(ref) for ref in references])} chars",
                f"(out) outline: {len(outline_creater_result.outline.to_text())} chars",
            ]
        )
    )
    # complete
    status.update(label="Reasoning Details", state="complete", expanded=False)
    ph.empty()

    id2reference = {i: search_result for i, search_result in enumerate(search_results, start=1)}

    # show
    outline = outline_creater_result.outline
    st.write("# " + outline.title)  # title
    summary_box = st.empty()  # summary（レポート完成後に生成）
    conclusion_section = st.empty()  # 結論セクション（サマリーの下に配置）
    logger.info("Created conclusion_section placeholder")
    lead_box = st.empty()  # lead
    mindmap_box = st.empty()  # mindmap
    section_boxes = [st.empty() for _ in outline.section_outlines]  # section

    with mindmap_box.container():
        mindmap = outline.to_text()
        logger.info("mindmap :\n" + mindmap)
        draw_mindmap(mindmap)
    stream_section_writers = [StreamSectionWriter(lm=lm) for _ in outline.section_outlines]
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
            if ref_id not in id2reference:
                logger.warning(f"invalid ref_id: {ref_id}")
                continue
            ref = id2reference[ref_id]
            refs.append(f"[{ref_id}] " + ref.title + "\n" + ref.snippet)
        refs = "\n\n".join(refs)
        tasks.append(write_section(section_box, stream_section_writer, query, refs, section_outline.to_text()))

    async def finish_section_writing():
        await asyncio.gather(*tasks)

    asyncio.run(finish_section_writing())

    # 結論を生成
    report_draft = "\n".join(["# " + outline.title] + [writer.section_content for writer in stream_section_writers])
    stream_conclusion_writer = StreamConclusionWriter(lm)

    # 結論セクションを表示
    logger.info("Starting conclusion generation")
    with conclusion_section.container():
        st.write("## 結論")
        # async generatorを同期的にStreamlitで表示（lead_boxと同じアプローチ）
        st.write_stream(stream_conclusion_writer(query, report_draft))
    conclusion = stream_conclusion_writer.conclusion
    logger.info(f"Generated conclusion length: {len(conclusion) if conclusion else 0}")
    logger.info(f"Conclusion content preview: {conclusion[:100] if conclusion else 'None'}")

    stream_lead_writer = StreamLeadWriter(lm=lm)
    report_draft = "\n".join(
        ["# " + outline.title]
        + [writer.section_content for writer in stream_section_writers]
        + ["## 結論", conclusion]
    )
    # Lead生成（結論の後）
    lead_box.write_stream(stream_lead_writer(query=query, title=outline.title, draft=report_draft))
    lead = stream_lead_writer.lead

    report_content = "\n".join(
        ["# " + outline.title, lead]
        + [writer.section_content for writer in stream_section_writers]
        + ["## 結論", conclusion]
    )

    # レポート完成後に違反サマリーを生成
    status.update(label="違反・問題点の分析...", state="running")
    violation_summarizer = ViolationSummarizer(lm=summary_lm)
    violation_analysis = violation_summarizer(query=query, report_content=report_content)
    logger.info(f"Violation analysis generated: {violation_analysis}")

    # サマリーを表示
    def get_severity_order(severity):
        """重要度の順序を返す（高→中→低）"""
        order_map = {"high": 0, "medium": 1, "low": 2}
        return order_map.get(severity, 3)  # 不明な重要度は最後

    def display_problem_with_severity(problem, index):
        """重要度に応じた問題の表示"""
        severity = problem.get("severity", "medium")
        problem_text = problem.get("problem", "")
        evidence = problem.get("evidence", "")
        recommended_action = problem.get("recommended_action", "")

        # 重要度に応じたアイコンと表示関数
        severity_config = {
            "high": {"icon": "🔴", "label": "高", "func": st.error},
            "medium": {"icon": "🟡", "label": "中", "func": st.warning},
            "low": {"icon": "🔵", "label": "低", "func": st.info},
        }

        config = severity_config.get(severity, severity_config["medium"])

        # すべての情報を1つのボックスにまとめて表示
        message_parts = [f"{config['icon']} **問題 {index} [重要度: {config['label']}]**", ""]
        message_parts.append(f"**問題内容:** {problem_text}")
        
        if evidence:
            message_parts.append(f"**該当箇所:** 「{evidence}」")
        
        if recommended_action:
            message_parts.append(f"**推奨対応:** {recommended_action}")
        
        config["func"]("\n\n".join(message_parts))

    with summary_box.container():
        with st.expander("**⚠️ 具体的な問題・違反と該当法律**", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                if violation_analysis.get("specific_problems") and len(violation_analysis["specific_problems"]) > 0:
                    st.markdown("**🚨 何が問題なのか**")

                    # 重要度でソート（高→中→低）
                    sorted_problems = sorted(
                        violation_analysis["specific_problems"],
                        key=lambda x: get_severity_order(x.get("severity", "medium")),
                    )

                    for i, problem in enumerate(sorted_problems, 1):
                        display_problem_with_severity(problem, i)
                else:
                    st.info("具体的な問題は検出されませんでした。")

            with col2:
                if violation_analysis.get("specific_laws") and len(violation_analysis["specific_laws"]) > 0:
                    st.markdown("**📖 どの法律に違反しているのか**")
                    for i, law in enumerate(violation_analysis["specific_laws"], 1):
                        st.warning(f"**該当法律 {i}**: {law.get('keyword', '不明')} ({law.get('type', '')})")
                        if law.get("full_name"):
                            st.caption(f"正式名称: {law['full_name']}")
                        if law.get("relevant_articles"):
                            st.caption(f"関連条文: {law['relevant_articles']}")
                else:
                    st.info("該当する法律は特定されませんでした。")

    # 結論セクションは既に表示済み（上記のwrite_conclusion_asyncで表示）
    # ここでの重複表示を削除

    # complete
    status.update(label="Reasoning Details", state="complete", expanded=False)

    st.write("## References")
    for i, result in enumerate(search_results, start=1):
        html = get_hiddenbox_ref_html(i, result)
        st.markdown(html, unsafe_allow_html=True)
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
        messages=messages,
        violation_analysis=violation_analysis,  # 違反分析結果を保存
    )
    logger.info(f"Report created with violation_analysis: {hasattr(new_report, 'violation_analysis')}")
    new_report.save(get_config("history_dir"))
    REPORT_PAGES[new_report.id] = st.Page(
        create_report_page(new_report), title=new_report.title, url_path=new_report.id
    )
    logger.info("saved report")

    st.switch_page(page=REPORT_PAGES[new_report.id])
