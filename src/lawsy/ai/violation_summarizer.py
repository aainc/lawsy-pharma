import os
import dspy
from typing import Dict, List
from lawsy.utils.logging import logger


def create_violation_summary_signature(max_items: int = 10):
    """動的にViolationSummaryシグネチャを作成"""
    class ViolationSummary(dspy.Signature):
        __doc__ = f"""あなたは日本の薬事法令に精通した専門家です。
        提供されたレポート内容を分析し、以下の2点を簡潔にまとめてください：
        
        1. 何が問題なのか（具体的な問題点・違反の可能性）
        2. どの法律に違反しているのか（該当する具体的な法律・省令）
        
        【分析のポイント】
        - レポートの内容から、法的に問題となりうる具体的な事項を抽出
        - 該当する法律・省令を正確に特定（薬機法、GCP省令、GMP省令、GPSP省令、GVP省令など）
        - 問題点は{max_items}個まで、法律も{max_items}個までに絞って最も重要なものを選択
        - 憶測や推測は避け、レポートに明記されている内容のみを根拠とする
        
        【出力形式】
        JSON形式で以下の構造を返してください：
        {{
            "specific_problems": [
                {{
                    "problem": "問題の内容（簡潔に）",
                    "evidence": "レポート内の根拠となる記述（抜粋）"
                }}
            ],
            "specific_laws": [
                {{
                    "keyword": "法律の略称（例：薬機法、GCP省令）",
                    "full_name": "法律の正式名称",
                    "type": "分類（基本法、治験関連、製造関連、安全管理関連など）",
                    "relevant_articles": "関連する条文番号（あれば）"
                }}
            ]
        }}
        """
        
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
            result = self.summarize(
                query=query,
                report_content=report_content
            )
            
        try:
            # JSON文字列をパース
            violation_data = json.loads(result.violation_summary)
            
            # データの整形と検証（max_itemsで制限）
            specific_problems = violation_data.get("specific_problems", [])[:self.max_items]
            specific_laws = violation_data.get("specific_laws", [])[:self.max_items]
            
            # 法律名のマッピング（正式名称が不足している場合の補完）
            law_mappings = {
                "薬機法": "医薬品、医療機器等の品質、有効性及び安全性の確保等に関する法律",
                "薬事法": "医薬品、医療機器等の品質、有効性及び安全性の確保等に関する法律",
                "GCP省令": "医薬品の臨床試験の実施の基準に関する省令",
                "GMP省令": "医薬品及び医薬部外品の製造管理及び品質管理の基準に関する省令",
                "GPSP省令": "医薬品の製造販売後の調査及び試験の実施の基準に関する省令",
                "GVP省令": "医薬品の製造販売後安全管理の基準に関する省令"
            }
            
            # 法律情報の補完
            for law in specific_laws:
                if "full_name" not in law and law.get("keyword") in law_mappings:
                    law["full_name"] = law_mappings[law["keyword"]]
            
            return {
                "specific_problems": specific_problems,
                "specific_laws": specific_laws,
                "has_violations": len(specific_problems) > 0
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse violation summary JSON: {e}")
            # フォールバック：空の結果を返す
            return {
                "specific_problems": [],
                "specific_laws": [],
                "has_violations": False
            }