import concurrent.futures
import os
from typing import Generator, Optional

import dspy
from loguru import logger


class WriteLead(dspy.Signature):
    """あなたは日本の法令に精通し、分かりやすい解説を書くことに定評のある信頼できるライターです。下記のクエリーに関する調査をしており、クエリーをもとにレポートのアウトラインを作成しました。アウトラインをもとに、レポート全体でどのような展開がなされるか、簡潔なリード文を作成してください。"""

    query = dspy.InputField(desc="クエリー", format=str)
    outline = dspy.InputField(desc="レポート全体のアウトライン", format=str)
    lead = dspy.OutputField(desc="生成されたリード文", format=str)


class WriteSection(dspy.Signature):
    """あなたは日本の法令に精通し、分かりやすい解説を書くことに定評のある信頼できるライターです。下記のクエリーに関する調査をしており、クエリーをもとにレポートのアウトラインを作成しました。
    アウトラインの中にある引用番号をもとに、収集された情報源の条文を適切に参照しながら各セクションの内容を記載してください。必ず各サブセクションごとに400字以上記載してください。解説は緻密かつ包括的で情報量が多く、情報源に基づいたものであることが望ましいです。法令に詳しくない人向けにわかりやすくかみ砕いて説明することも重要です。必要に応じて、用いている法令の概要、関連法規、適切な事例、歴史的背景、最新の判例などを盛り込んでください。
    なお、内容の信頼性が重要なので、必ず情報源にあたり、下記指示にあるように引用をするのを忘れないで下さい。
    1. アウトラインの"# Title"、"## Title"、"### Title"のタイトルは変更しないでください。
    2. 必ず情報源の情報に基づき記載し、ハルシネーションに気をつけること。
       記載の根拠となる参照すべき情報源は "...です[4][1][27]。" "...ます[21][9]。" のように明示。
       その記述に対しての関連性が高そうな順に付与してください。
    3. 正しく引用を明示されているほどあなたの解説は高く評価されます。
       引用なしの創作は論拠が明確でない限り全く評価されません。
    4. 情報源を解説の末尾に含める必要はありません。
    5. 日本語のですます調で解説を書いてください。

    """

    query = dspy.InputField(desc="クエリー", format=str)
    references = dspy.InputField(desc="収集された情報源と引用番号", format=str)
    section_outline = dspy.InputField(desc="セクションのアウトライン", format=str)
    section = dspy.OutputField(desc="生成されたセクション", format=str)


class WriteConclusion(dspy.Signature):
    """あなたは日本の法令に精通し、分かりやすい解説を書くことに定評のある信頼できるライターです。
    レポートのドラフトを踏まえて、レポート全体の結論（テーマを明確にし、背景を説明し、その話題がなぜ重要なのかを提示、最も重要なポイントや主要な論争があれば要約）と今後の方向性やユーザーの取るべきネクストアクションを生成します。最低でも400字以上、可能なら600字以上記載してください。
    そして、生成したconclusionの冒頭に"## 結論"という行を追記してください。
    """

    query = dspy.InputField(desc="クエリー", format=str)
    report_draft = dspy.InputField(desc="レポートのドラフト", format=str)
    conclusion = dspy.OutputField(desc="生成された結論", format=str)


# dspyのstreamifyはstreamlitと相性が悪いようでうまく動かなかったので独自にstream出力を実装
class StreamReportWriter:
    def __init__(self, lm) -> None:
        self.lm = lm
        self.write_section = dspy.Predict(WriteSection)
        self.write_conclusion = dspy.Predict(WriteConclusion)
        self.write_lead = dspy.Predict(WriteLead)
        self.max_thread_num = min(20, (os.cpu_count() or 5) * 2)
        self.text = ""

    def _split_outline(self, outline: str):
        lines = outline.splitlines()
        overall_title = ""
        sections = []
        current_section = []
        for line in lines:
            if line.startswith("# ") and not line.startswith("##"):
                overall_title = line.strip()
            elif line.startswith("## "):
                if current_section:
                    sections.append("\n".join(current_section))
                    current_section = []
                current_section.append(line.strip())
            elif current_section:
                current_section.append(line.strip())
        if current_section:
            sections.append("\n".join(current_section))
        return overall_title, sections

    def _generate_section(self, query: str, references_text: str, section_outline: str) -> str:
        with dspy.settings.context(lm=self.lm):
            result = self.write_section(query=query, references=references_text, section_outline=section_outline)
        return result.section

    def __call__(self, query: str, outline: str, references: list[str]) -> Generator[str, None, None]:
        references_text = "\n\n".join(references)
        overall_title, sections = self._split_outline(outline)

        # 最初に全体タイトルをyield
        yield overall_title + "\n"

        # リード文を生成してyieldする
        with dspy.settings.context(lm=self.lm):
            lead_result = self.write_lead(query=query, outline=outline)
        lead_text = lead_result.lead
        yield lead_text + "\n"

        # 各セクションを並列処理で生成
        section_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_thread_num) as executor:
            future_to_idx = {
                executor.submit(self._generate_section, query, references_text, sec_outline): idx
                for idx, sec_outline in enumerate(sections)
            }

            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    section_results[idx] = future.result()
                except Exception as exc:
                    section_results[idx] = f"Error in section {idx}: {exc}"

        # 順序通りにセクションを `yield` していく
        report_sections = ""
        for idx in sorted(section_results.keys()):
            section_text = section_results[idx]
            report_sections += section_text + "\n"
            yield section_text + "\n"

        # 結論生成
        report_draft = overall_title + "\n" + lead_text + "\n" + report_sections + "\n"
        with dspy.settings.context(lm=self.lm):
            concl_result = self.write_conclusion(query=query, report_draft=report_draft)
        conclusion_text = concl_result.conclusion
        yield conclusion_text + "\n"

        # 最終レポートの完成
        final_report = report_draft + "\n" + conclusion_text
        self.text = final_report
        logger.info("stream generation: " + final_report)
        # yield final_report + "\n"

    def get_text(self):
        return self.text


class ReportWriter(dspy.Module):
    def __init__(self, lm, max_thread_num: Optional[int] = None) -> None:
        self.lm = lm
        # CPU数に応じた最大スレッド数の設定（明示的に指定がない場合）
        if max_thread_num is None:
            self.max_thread_num = min(20, (os.cpu_count() or 5) * 2)
        else:
            self.max_thread_num = max_thread_num
        # 各セクション・結論・リード生成用のPredictを初期化
        self.write_section = dspy.Predict(WriteSection)
        self.write_conclusion = dspy.Predict(WriteConclusion)
        self.write_lead = dspy.Predict(WriteLead)

    def _split_outline(self, outline: str):
        lines = outline.splitlines()
        overall_title = ""
        sections = []
        current_section = []
        for line in lines:
            if line.startswith("# ") and not line.startswith("##"):
                overall_title = line.strip()
            elif line.startswith("## "):
                if current_section:
                    sections.append("\n".join(current_section))
                    current_section = []
                current_section.append(line.strip())
            elif current_section:
                current_section.append(line.strip())
        if current_section:
            sections.append("\n".join(current_section))
        return overall_title, sections

    def _generate_section(self, query: str, references_text: str, section_outline: str) -> str:
        with dspy.settings.context(lm=self.lm):
            result = self.write_section(query=query, references=references_text, section_outline=section_outline)
        return result.section

    def forward(self, query: str, outline: str, references: list[str]) -> dspy.Prediction:
        references_text = "\n\n".join(references)
        overall_title, sections = self._split_outline(outline)

        # アウトラインを踏まえてリード文を生成
        with dspy.settings.context(lm=self.lm):
            lead_result = self.write_lead(query=query, outline=outline)
        lead_text = lead_result.lead

        section_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_thread_num) as executor:
            future_to_idx = {
                executor.submit(self._generate_section, query, references_text, sec_outline): idx
                for idx, sec_outline in enumerate(sections)
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    section_results[idx] = future.result()
                except Exception as exc:
                    section_results[idx] = f"Error in section {idx}: {exc}"

        # 順序通りに各セクションの生成結果を連結
        report_sections = ""
        for idx in sorted(section_results.keys()):
            report_sections += section_results[idx] + "\n"

        # 全体タイトル、リード文、本文を連結してドラフトとする
        report_draft = overall_title + "\n" + lead_text + "\n" + report_sections

        # 統合した各セクションを元に結論を生成
        with dspy.settings.context(lm=self.lm):
            concl_result = self.write_conclusion(query=query, report_draft=report_draft)
        conclusion_text = concl_result.conclusion

        # ドラフトに結論を追加して最終レポートとする
        final_report = report_draft + "\n" + conclusion_text

        return dspy.Prediction(report=final_report)
