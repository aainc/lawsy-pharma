import os
from typing import Dict

import dspy

from lawsy.utils.logging import logger


def create_violation_summary_signature(max_items: int = 10):
    """動的にViolationSummaryシグネチャを作成"""
    from .violation_summary_prompt import ViolationSummaryPromptBuilder
    
    # ViolationSummaryPromptBuilderを使用してプロンプトを取得
    prompt_builder = ViolationSummaryPromptBuilder()
    prompt_text = prompt_builder.build_prompt_text(max_items)

    class ViolationSummary(dspy.Signature):
        __doc__ = prompt_text  # 固定文字列から動的生成に変更

        query: str = dspy.InputField(desc="ユーザーの質問内容")
        report_content: str = dspy.InputField(desc="生成されたレポート全文")
        violation_summary: str = dspy.OutputField(desc="違反分析結果（JSON形式）")

    return ViolationSummary


class ViolationSummarizer(dspy.Module):
    def __init__(self, lm):
        super().__init__()
        self.lm = lm
        # 環境変数から最大表示数を取得（デフォルト: 10）
        self.max_items = int(os.getenv("LAWSY_VIOLATION_SUMMARY_MAX_ITEMS", "10"))
        logger.info(f"ViolationSummarizer max_items: {self.max_items}")
        # 動的にシグネチャを作成
        ViolationSummaryClass = create_violation_summary_signature(self.max_items)
        self.summarize = dspy.Predict(ViolationSummaryClass)

    def forward(self, query: str, report_content: str) -> Dict:
        """レポート内容から違反・問題点を分析"""
        import json

        with dspy.settings.context(lm=self.lm):
            result = self.summarize(query=query, report_content=report_content)

        try:
            # JSON文字列をパース
            violation_data = json.loads(result.violation_summary)

            # データの整形と検証
            specific_problems = violation_data.get("specific_problems", [])
            specific_laws = violation_data.get("specific_laws", [])

            # 薬機法関連法令のキーワードリスト
            pharma_law_keywords = [
                "薬機法",
                "薬事法",
                "GCP",
                "GMP",
                "GPSP",
                "GVP",
                "QMS",
                "GQP",
                "医薬品",
                "医療機器",
                "体外診断",
                "再生医療",
                "製造販売",
                "臨床試験",
                "治験",
                "品質管理",
                "安全管理",
            ]

            # 薬機法関連のみをフィルタリング
            filtered_laws = []
            for law in specific_laws:
                keyword = law.get("keyword", "")
                # キーワードが薬機法関連かチェック
                if any(pharma_keyword in keyword for pharma_keyword in pharma_law_keywords):
                    filtered_laws.append(law)
                    if len(filtered_laws) >= self.max_items:
                        break

            # max_itemsで制限
            specific_problems = specific_problems[: self.max_items]
            specific_laws = filtered_laws[: self.max_items]

            # 法律名のマッピング（正式名称が不足している場合の補完）
            law_mappings = {
                "薬機法": "医薬品、医療機器等の品質、有効性及び安全性の確保等に関する法律",
                "薬事法": "医薬品、医療機器等の品質、有効性及び安全性の確保等に関する法律",
                "GCP省令": "医薬品の臨床試験の実施の基準に関する省令",
                "GMP省令": "医薬品及び医薬部外品の製造管理及び品質管理の基準に関する省令",
                "GPSP省令": "医薬品の製造販売後の調査及び試験の実施の基準に関する省令",
                "GVP省令": "医薬品の製造販売後安全管理の基準に関する省令",
                "QMS省令": "医療機器及び体外診断用医薬品の製造管理及び品質管理の基準に関する省令",
                "GQP省令": "医薬品、医薬部外品、化粧品及び再生医療等製品の品質管理の基準に関する省令",
            }

            # 法律情報の補完
            for law in specific_laws:
                if "full_name" not in law and law.get("keyword") in law_mappings:
                    law["full_name"] = law_mappings[law["keyword"]]

            return {
                "specific_problems": specific_problems,
                "specific_laws": specific_laws,
                "has_violations": len(specific_problems) > 0,
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse violation summary JSON: {e}")
            # フォールバック：空の結果を返す
            return {"specific_problems": [], "specific_laws": [], "has_violations": False}
