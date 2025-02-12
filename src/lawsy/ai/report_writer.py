import concurrent.futures
import os
from typing import Generator

import dspy
from loguru import logger


class WriteSection(dspy.Signature):
    """あなたは日本の法令に精通し、分かりやすい解説を書くことに定評のある信頼できるライターです。下記のクエリーに関する調査をしており、クエリーをもとにレポートのアウトラインを作成しました。
    アウトラインの中にある引用番号をもとに、収集された情報源の条文を適切に参照しながら各セクションの内容を記載してください。必ず各サブセクションごとに400字以上記載してください。解説は緻密かつ包括的で情報量が多く、情報源に基づいたものであることが望ましいです。法令に詳しくない人向けにわかりやすくかみ砕いて説明することも重要です。必要に応じて、用いている法令の概要、関連法規、適切な事例、歴史的背景、最新の判例などを盛り込んでください。
    なお、内容の信頼性が重要なので、必ず情報源にあたり、下記指示にあるように引用をするのを忘れないで下さい。
    1. アウトラインの"# Title"、"## Title"、"### Title"のタイトルは変更しないでください。
    2. 必ず情報源の情報に基づき記載し、ハルシネーションに気をつけること。
       記載の根拠となる参照すべき情報源は "...です[4][1][27]。" "...ます[21][9]。" のように明示い。
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
    統合した各セクションを踏まえて、レポート全体の結論と今後の方向性やネクストアクションを生成します。
    そして、生成したconclusionの冒頭に"## 結論"という行を追記してください。"""

    query = dspy.InputField(desc="クエリー", format=str)
    report_sections = dspy.InputField(desc="統合した各セクションの文章", format=str)
    conclusion = dspy.OutputField(desc="生成された結論", format=str)


class WriteLead(dspy.Signature):
    """あなたは日本の法令に精通し、分かりやすい解説を書くことに定評のある信頼できるライターです。統合した最終レポート全体を踏まえて、レポートのリード文を生成します。最低でも400字以上、可能なら600字以上記載し、ドラフトに追記してください。なお、リードセクションは記事の簡潔な概要として独立して成り立つものにすること（テーマを明確にし、背景を説明し、その話題がなぜ重要なのかを提示、最も重要なポイントや主要な論争があれば要約）"""

    query = dspy.InputField(desc="クエリー", format=str)
    report_draft = dspy.InputField(desc="統合したレポート本文（結論含む）", format=str)
    lead = dspy.OutputField(desc="生成されたリード文", format=str)


# dspyのstreamifyはstreamlitと相性が悪いようでうまく動かなかったので独自にstream出力を実装
class StreamReportWriter:
    def __init__(self, lm) -> None:
        self.lm = lm
        self.write_section = dspy.Predict(WriteSection)
        self.write_conclusion = dspy.Predict(WriteConclusion)
        self.write_lead = dspy.Predict(WriteLead)
        self.max_thread_num = min(20, os.cpu_count() * 2)
        self.text = ""

    def _split_outline(self, outline: str):
        """
        アウトライン文字列から、全体タイトル（先頭の "# Title"）と各セクション（"## Title"～以降）を抽出します。
        """
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

        # 各セクションを順次生成してyieldする
        report_sections = ""
        for idx, sec_outline in enumerate(sections):
            section_text = self._generate_section(query, references_text, sec_outline)
            report_sections += section_text + "\n"
            yield section_text + "\n"  # セクション生成後に逐次出力

        # 結論生成
        with dspy.settings.context(lm=self.lm):
            concl_result = self.write_conclusion(query=query, report_sections=report_sections)
        conclusion_text = concl_result.conclusion
        yield conclusion_text + "\n"  # 結論生成後に出力

        # 下書き（セクション＋結論）を元にリード文生成
        report_draft = report_sections + "\n" + conclusion_text
        with dspy.settings.context(lm=self.lm):
            lead_result = self.write_lead(query=query, report_draft=report_draft)
        lead_text = lead_result.lead
        yield lead_text + "\n"  # リード文生成後に出力

        # 最終レポートの完成
        final_report = overall_title + "\n" + lead_text + "\n" + report_draft
        self.text = final_report
        logger.info("stream generation: " + final_report)
        # yield final_report + "\n"

    def get_text(self):
        return self.text


class ReportWriter(dspy.Module):
    def __init__(self, lm, max_thread_num: int = None) -> None:
        self.lm = lm
        # CPU数に応じた最大スレッド数の設定（明示的に指定がない場合）
        if max_thread_num is None:
            self.max_thread_num = min(20, os.cpu_count() * 2)
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
        """
        1. topicsリストから Markdownアウトラインを自動生成する。
        2. アウトラインを解析して、全体タイトルと各セクションのアウトラインに分割する。
        3. 並列処理により各セクションを生成する。
        4. 各セクションを統合した本文から、結論を生成する。
        5. 結論を含む下書きをもとにリード文を生成し、全体レポートを組み立てる。
        """
        references_text = "\n\n".join(references)
        overall_title, sections = self._split_outline(outline)

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

        # 統合した各セクションを元に結論を生成
        with dspy.settings.context(lm=self.lm):
            concl_result = self.write_conclusion(query=query, report_sections=report_sections)
        conclusion_text = concl_result.conclusion

        # 結論を含む下書きの本文を作成
        report_draft = report_sections + "\n" + conclusion_text

        # 下書きを踏まえてリード文を生成
        with dspy.settings.context(lm=self.lm):
            lead_result = self.write_lead(query=query, report_draft=report_draft)
        lead_text = lead_result.lead

        # 全体タイトル、リード文、本文を連結して最終レポートとする
        final_report = overall_title + "\n" + lead_text + "\n" + report_draft

        return dspy.Prediction(report=final_report)
