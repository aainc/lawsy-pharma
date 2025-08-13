import json
import re
from pathlib import Path
from typing import Dict, List, Optional


class PharmaTermsProcessor:
    """薬事法専門用語の処理クラス"""
    
    def __init__(self, terms_file_path: Optional[str] = None):
        if terms_file_path is None:
            # デフォルトパスを設定
            terms_file_path = Path(__file__).parent.parent / "data" / "pharma_terms.json"
        
        self.terms_file_path = Path(terms_file_path)
        self.terms_data = self._load_terms()
    
    def _load_terms(self) -> Dict:
        """薬事専門用語辞書を読み込む"""
        try:
            with open(self.terms_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # ファイルが見つからない場合は空の辞書を返す
            return {
                "abbreviations": {},
                "synonyms": {},
                "categories": {},
                "regulations": {},
                "license_types": {}
            }
    
    def expand_abbreviations(self, text: str) -> str:
        """略語を正式名称に展開"""
        expanded_text = text
        abbreviations = self.terms_data.get("abbreviations", {})
        
        for abbr, full_name in abbreviations.items():
            # 完全一致での置換（単語境界を考慮）
            pattern = r'\b' + re.escape(abbr) + r'\b'
            expanded_text = re.sub(pattern, f"{abbr}（{full_name}）", expanded_text, flags=re.IGNORECASE)
        
        return expanded_text
    
    def add_synonyms(self, query: str) -> List[str]:
        """同義語を追加した検索クエリのリストを生成"""
        queries = [query]
        synonyms = self.terms_data.get("synonyms", {})
        
        for term, synonym_list in synonyms.items():
            if term in query:
                for synonym in synonym_list:
                    # 元の用語を同義語に置換した新しいクエリを追加
                    new_query = query.replace(term, synonym)
                    if new_query not in queries:
                        queries.append(new_query)
        
        return queries
    
    def enhance_query_with_context(self, query: str) -> str:
        """薬事法の文脈を考慮してクエリを強化"""
        enhanced_query = query
        categories = self.terms_data.get("categories", {})
        
        # クエリに含まれる用語のカテゴリを特定
        relevant_categories = []
        for category, terms in categories.items():
            for term in terms:
                if term in query:
                    relevant_categories.append(category)
                    break
        
        # 関連するカテゴリの用語を追加候補として提案
        if relevant_categories:
            category_terms = []
            for category in relevant_categories:
                category_terms.extend(categories[category][:3])  # 上位3つまで
            
            if category_terms:
                enhanced_query += f" 関連用語: {', '.join(set(category_terms))}"
        
        return enhanced_query
    
    def get_regulation_context(self, query: str) -> List[str]:
        """クエリに関連する法令・規制の情報を取得"""
        regulations = self.terms_data.get("regulations", {})
        license_types = self.terms_data.get("license_types", {})
        
        relevant_regs = []
        
        # 法令名の直接マッチング
        for reg_key, reg_full_name in regulations.items():
            if reg_key in query or reg_full_name in query:
                relevant_regs.append(reg_full_name)
        
        # 許可・免許関連の用語チェック
        for license_key, license_full_name in license_types.items():
            if license_key in query or "許可" in query or "免許" in query:
                relevant_regs.append(license_full_name)
        
        return list(set(relevant_regs))


def enhance_pharma_query(query: str, terms_processor: Optional[PharmaTermsProcessor] = None) -> Dict[str, any]:
    """薬事法クエリの総合的な強化処理"""
    if terms_processor is None:
        terms_processor = PharmaTermsProcessor()
    
    # 略語展開
    expanded_query = terms_processor.expand_abbreviations(query)
    
    # 同義語を含む検索クエリリスト生成
    synonym_queries = terms_processor.add_synonyms(query)
    
    # 文脈強化
    enhanced_query = terms_processor.enhance_query_with_context(expanded_query)
    
    # 関連法令情報
    relevant_regulations = terms_processor.get_regulation_context(query)
    
    return {
        "original_query": query,
        "expanded_query": expanded_query,
        "enhanced_query": enhanced_query,
        "synonym_queries": synonym_queries,
        "relevant_regulations": relevant_regulations
    }