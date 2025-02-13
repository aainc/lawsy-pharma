import concurrent.futures
import os
import re
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
    """あなたは日本の法令に精通し、分かりやすい解説を書くことに定評のある信頼できるライターです。レポートのドラフトを踏まえて、レポート全体の要約を本文とはできるだけ異なる表現で記載しつつ、今後の方向性や対応策を生成します。最低でも400字以上、可能なら600字以上記載してください。
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

    def _parse_references(self, references: list[str]) -> dict[int, str]:
        """リファレンスリストを {番号: 内容} の辞書に変換"""
        references_dict = {}
        for ref in references:
            match = re.match(r"\[(\d+)\]\s*(.+)", ref, re.DOTALL)
            if match:
                ref_num = int(match.group(1))  # 例: "[1]" → 1
                references_dict[ref_num] = f"[{ref_num}] {match.group(2)}"
        return references_dict

    def _extract_references_from_outline(self, section_outline: str) -> list[int]:
        """セクションのアウトラインから引用番号を抽出"""
        reference_ids = list(map(int, re.findall(r"\[(\d+)\]", section_outline)))
        return reference_ids

    def _generate_section(self, query: str, references_dict: dict[int, str], section_outline: str) -> str:
        """該当するリファレンスのみを参照してセクションを生成"""
        # 1. セクション内で実際に使われている引用番号を抽出
        reference_ids = self._extract_references_from_outline(section_outline)

        # 2. 必要なリファレンスのみを選別
        filtered_references = "\n\n".join([references_dict[rid] for rid in reference_ids if rid in references_dict])

        # 3. dspy を用いてセクションを生成
        with dspy.settings.context(lm=self.lm):
            result = self.write_section(query=query, references=filtered_references, section_outline=section_outline)

        return result.section

    def __call__(self, query: str, outline: str, references: list[str]) -> Generator[str, None, None]:
        """ストリーミングでレポートを生成"""

        # 1. リファレンスを {番号: 内容} の辞書に変換
        references_dict = self._parse_references(references)

        # 2. アウトラインを分割
        overall_title, sections = self._split_outline(outline)

        # 3. 最初に全体タイトルをyield
        yield overall_title + "\n"

        # 4. リード文を生成してyieldする
        with dspy.settings.context(lm=self.lm):
            lead_result = self.write_lead(query=query, outline=outline)
        lead_text = lead_result.lead
        yield lead_text + "\n"

        # 5. 各セクションを並列処理で生成
        section_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_thread_num) as executor:
            future_to_idx = {
                executor.submit(self._generate_section, query, references_dict, sec_outline): idx
                for idx, sec_outline in enumerate(sections)
            }

            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    section_results[idx] = future.result()
                except Exception as exc:
                    section_results[idx] = f"Error in section {idx}: {exc}"

        # 6. 順序通りにセクションを `yield` していく
        report_sections = ""
        for idx in sorted(section_results.keys()):
            section_text = section_results[idx]
            report_sections += section_text + "\n"
            yield section_text + "\n"

        # 7. 結論生成
        report_draft = overall_title + "\n" + lead_text + "\n" + report_sections + "\n"
        with dspy.settings.context(lm=self.lm):
            concl_result = self.write_conclusion(query=query, report_draft=report_draft)
        conclusion_text = concl_result.conclusion
        yield conclusion_text + "\n"

        # 8. 最終レポートの完成
        final_report = report_draft + "\n" + conclusion_text
        self.text = final_report
        logger.info("stream generation: " + final_report)

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

    def _parse_references(self, references: list[str]) -> dict[int, str]:
        """リファレンスリストを {番号: 内容} の辞書に変換"""
        references_dict = {}
        for ref in references:
            match = re.match(r"\[(\d+)\]\s*(.+)", ref, re.DOTALL)
            if match:
                ref_num = int(match.group(1))  # 例: "[1]" → 1
                references_dict[ref_num] = f"[{ref_num}] {match.group(2)}"
        return references_dict

    def _extract_references_from_outline(self, section_outline: str) -> list[int]:
        """セクションのアウトラインから引用番号を抽出"""
        return list(map(int, re.findall(r"\[(\d+)\]", section_outline)))

    def _generate_section(self, query: str, references_dict: dict[int, str], section_outline: str) -> str:
        """該当するリファレンスのみを参照してセクションを生成"""
        # 1. セクション内で実際に使われている引用番号を抽出
        reference_ids = self._extract_references_from_outline(section_outline)

        # 2. 必要なリファレンスのみを選別
        filtered_references = "\n\n".join([references_dict[rid] for rid in reference_ids if rid in references_dict])

        # 3. dspy を用いてセクションを生成
        with dspy.settings.context(lm=self.lm):
            result = self.write_section(query=query, references=filtered_references, section_outline=section_outline)

        return result.section

    def forward(self, query: str, outline: str, references: list[str]) -> dspy.Prediction:
        """各セクションのリファレンスを適切に絞り込んで処理を並列化"""

        # 1. リファレンスを {番号: 内容} の辞書に変換
        references_dict = self._parse_references(references)

        # 2. アウトラインを分割
        overall_title, sections = self._split_outline(outline)

        # 3. リード文を生成
        with dspy.settings.context(lm=self.lm):
            lead_result = self.write_lead(query=query, outline=outline)
        lead_text = lead_result.lead

        # 4. 各セクションを並列処理
        section_results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_thread_num) as executor:
            future_to_idx = {
                executor.submit(self._generate_section, query, references_dict, sec_outline): idx
                for idx, sec_outline in enumerate(sections)
            }
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    section_results[idx] = future.result()
                except Exception as exc:
                    section_results[idx] = f"Error in section {idx}: {exc}"

        # 5. 順序通りに各セクションの生成結果を連結
        report_sections = "\n".join(section_results[idx] for idx in sorted(section_results.keys()))
        report_draft = f"{overall_title}\n{lead_text}\n{report_sections}"

        # 6. 結論を生成
        with dspy.settings.context(lm=self.lm):
            concl_result = self.write_conclusion(query=query, report_draft=report_draft)
        conclusion_text = concl_result.conclusion

        # 7. 最終レポート作成
        final_report = f"{report_draft}\n{conclusion_text}"

        return dspy.Prediction(report=final_report)
