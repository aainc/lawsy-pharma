import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ViolationSummaryPromptBuilder:
    """違反サマリー用のプロンプトを構築するクラス"""
    
    def __init__(self):
        self.target_audience = os.getenv("LAWSY_VIOLATION_SUMMARY_AUDIENCE", "expert")
        self.prompt_style = os.getenv("LAWSY_VIOLATION_SUMMARY_STYLE", "formal")
        self.template_path = os.getenv("LAWSY_VIOLATION_SUMMARY_TEMPLATE_PATH")
        
        # テンプレートディレクトリのパス
        self.templates_dir = Path(__file__).parent.parent.parent.parent / "prompts" / "violation_summary"
    
    def load_template(self) -> Dict[str, Any]:
        """テンプレートファイルを読み込んで返す"""
        if self.target_audience == "custom" and self.template_path:
            # カスタムテンプレートを読み込み
            template_file = Path(self.template_path)
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                # カスタムテンプレートが見つからない場合はexpertにフォールバック
                return self._load_default_template("expert")
        else:
            # デフォルトテンプレートを読み込み
            return self._load_default_template(self.target_audience)
    
    def _load_default_template(self, audience_type: str) -> Dict[str, Any]:
        """デフォルトテンプレートを読み込む"""
        template_file = self.templates_dir / f"{audience_type}.yaml"
        
        if template_file.exists():
            with open(template_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            # テンプレートファイルが存在しない場合は、現在のハードコード内容を返す
            return self._get_fallback_template()
    
    def _get_fallback_template(self) -> Dict[str, Any]:
        """フォールバック用のテンプレート（現在のハードコード内容）"""
        return {
            "audience": {
                "type": "expert",
                "description": "薬機法の専門家"
            },
            "prompt": {
                "role": "あなたは日本の薬機法令に精通した専門家です。",
                "task": """ユーザーの質問内容とレポート内容を分析し、以下の3点を簡潔にまとめてください：

        1. 何が問題なのか（具体的な問題点・違反の可能性）
        2. どの法律に違反しているのか（該当する具体的な法律・省令）
        3. 問題の重要度（高・中・低の3段階評価）""",
                "important_instructions": """【極めて重要な指示】
        - **evidenceフィールドには、ユーザーの質問文から問題となる具体的な記述を必ず引用**
        - レポートからの引用は絶対に使用しない
        - ユーザーが「〜したい」「〜できますか」「〜について」と書いた部分をそのまま引用
        - 引用は正確に、省略せずに、原文のまま記載すること""",
                "severity_criteria": {
                    "high": "表現修正では回避不可能な構造的・根本的な問題",
                    "medium": "表現修正や手続きで回避可能だが要注意な問題", 
                    "low": "予防的・推奨レベルの改善点"
                },
                "restrictions": """【重要な制限事項】
        - **薬機法関連の法律・省令のみを対象とすること**
        - 景表法、独占禁止法、個人情報保護法などの薬機法以外の法律は除外
        - 薬機法と併記されていても、薬機法以外の法律単独での違反は取り上げない"""
            }
        }
    
    def build_prompt_text(self, max_items: int = 10) -> str:
        """テンプレートからプロンプト文字列を構築"""
        template = self.load_template()
        return self._format_prompt(template, max_items)
    
    def _format_prompt(self, template: Dict[str, Any], max_items: int) -> str:
        """テンプレートの内容を使ってプロンプトを組み立てる"""
        prompt_data = template.get("prompt", {})
        
        # 基本的な構造を構築
        prompt_parts = []
        
        # 役割定義
        if "role" in prompt_data:
            prompt_parts.append(prompt_data["role"])
        
        # タスク説明
        if "task" in prompt_data:
            prompt_parts.append(prompt_data["task"])
        
        # 重要な指示
        if "important_instructions" in prompt_data:
            prompt_parts.append(prompt_data["important_instructions"])
        
        # 重要度判定基準
        if "severity_criteria" in prompt_data:
            criteria = prompt_data["severity_criteria"]
            criteria_text = "\n【重要度判定基準】\n"
            if isinstance(criteria, dict):
                for level, description in criteria.items():
                    criteria_text += f"**{level.upper()}**: {description}\n"
            else:
                criteria_text += str(criteria)
            prompt_parts.append(criteria_text)
        
        # 制限事項
        if "restrictions" in prompt_data:
            prompt_parts.append(prompt_data["restrictions"])
        
        # 推奨対応方法（テンプレートにある場合のみ）
        if "recommended_actions" in prompt_data:
            actions = prompt_data["recommended_actions"]
            actions_text = "\n【推奨対応方法の指針】\n"
            if isinstance(actions, dict):
                for level, description in actions.items():
                    actions_text += f"**{level.upper()}**: {description}\n"
            prompt_parts.append(actions_text)
        
        # 対象とする薬機法関連法令（現在のハードコード内容を保持）
        pharma_laws_text = """【対象とする薬機法関連法令】
        - 薬機法（医薬品、医療機器等の品質、有効性及び安全性の確保等に関する法律）
        - GCP省令（医薬品の臨床試験の実施の基準に関する省令）
        - GMP省令（医薬品及び医薬部外品の製造管理及び品質管理の基準に関する省令）
        - GPSP省令（医薬品の製造販売後の調査及び試験の実施の基準に関する省令）
        - GVP省令（医薬品の製造販売後安全管理の基準に関する省令）
        - QMS省令（医療機器及び体外診断用医薬品の製造管理及び品質管理の基準に関する省令）
        - GQP省令（医薬品、医薬部外品、化粧品及び再生医療等製品の品質管理の基準に関する省令）
        - その他の薬機関連省令・通知"""
        prompt_parts.append(pharma_laws_text)
        
        # 分析ポイント
        analysis_points = f"""【分析のポイント】
        - ユーザーの質問文を分析し、薬機法的に問題となりうる行為・状況を特定
        - 問題となる箇所は必ずユーザーの質問文から原文のまま引用
        - 該当する法律はレポートの内容を参考に特定
        - 問題点は{max_items}個まで、法律も{max_items}個までに絞って最も重要なものを選択
        - 各問題について重要度を適切に判定
        - 各問題に対して具体的で実行可能な対応方法を提案"""
        prompt_parts.append(analysis_points)
        
        # 出力形式
        output_format = f"""【出力形式】
        JSON形式で以下の構造を返してください：
        {{
            "specific_problems": [
                {{
                    "problem": "問題の内容（簡潔に）",
                    "evidence": "ユーザーの質問文から問題となる箇所を正確に引用（必須）",
                    "severity": "重要度（high/medium/low）",
                    "recommended_action": "推奨する対応方法（具体的で実行可能な内容）"
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
        }}"""
        prompt_parts.append(output_format)
        
        # 全体を結合
        return "\n\n".join(prompt_parts)