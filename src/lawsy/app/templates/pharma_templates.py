"""薬事法検索テンプレート"""

PHARMA_SEARCH_TEMPLATES = {
    "承認申請": {
        "title": "承認申請関連",
        "description": "新薬の承認申請、変更申請、更新申請等に関する情報",
        "templates": [
            "新薬の製造販売承認申請に必要な資料と手続きについて",
            "医薬品の一部変更承認申請の要件と注意点",
            "承認申請における照会事項への対応方法",
            "CTD（共通技術文書）の作成要領と留意事項",
            "承認審査期間の短縮制度（先駆け審査指定等）について",
        ],
    },
    "GMP関連": {
        "title": "GMP（医薬品製造管理・品質管理）",
        "description": "製造所のGMP基準、査察対応、品質管理等",
        "templates": [
            "GMP省令の改正内容と対応すべき事項について",
            "GMP査察での指摘事項と改善対応策",
            "製造所におけるバリデーション実施要領",
            "逸脱処理とCAPAシステムの運用方法",
            "原薬製造におけるGMP管理の注意点",
        ],
    },
    "臨床試験": {
        "title": "GCP・治験関連",
        "description": "治験の実施、GCP基準、被験者保護等",
        "templates": [
            "治験実施計画書の作成要領と必須記載事項",
            "GCP査察での確認事項と対応方法",
            "治験における有害事象報告の要件と手続き",
            "被験者の同意取得プロセスと同意書作成",
            "治験薬の管理と品質確保について",
        ],
    },
    "安全性": {
        "title": "GVP・安全性情報",
        "description": "副作用報告、安全性情報の収集・評価・提供",
        "templates": [
            "副作用等報告の要件と報告期限について",
            "定期的安全性最新報告書（PSUR）の作成方法",
            "安全性情報の収集体制と評価プロセス",
            "リスク管理計画（RMP）の策定と実施",
            "緊急安全性情報の配布基準と手続き",
        ],
    },
    "市販後調査": {
        "title": "GPSP・市販後調査",
        "description": "使用成績調査、製造販売後臨床試験等",
        "templates": [
            "使用成績調査の実施計画と調査項目設定",
            "特定使用成績調査における対象患者選定",
            "製造販売後臨床試験の実施要領",
            "市販後調査データの信頼性確保",
            "調査結果の解析と当局報告",
        ],
    },
    "許可・免許": {
        "title": "許可・免許制度",
        "description": "製造販売業許可、製造業許可等の取得・維持",
        "templates": [
            "製造販売業許可の取得要件と申請手続き",
            "製造業許可における構造設備基準",
            "許可更新時の注意事項と準備事項",
            "総括製造販売責任者の要件と責務",
            "製造所における責任技術者の役割",
        ],
    },
    "薬機法改正": {
        "title": "薬機法改正・制度変更",
        "description": "法令改正、新制度導入等の最新動向",
        "templates": [
            "薬機法改正による新制度への対応方法",
            "添付文書の記載要領変更に伴う対応",
            "医療機器プログラムの薬機法上の取扱い",
            "条件付き早期承認制度の活用方法",
            "薬事規制の国際調和への対応",
        ],
    },
    "品質管理": {
        "title": "品質管理・品質保証",
        "description": "品質システム、規格試験、安定性試験等",
        "templates": [
            "医薬品の品質システム構築と運用",
            "規格及び試験方法の設定根拠",
            "安定性試験の実施要領と評価方法",
            "変更管理システムの構築と運用",
            "供給者管理と委託先監査",
        ],
    },
}


def get_template_categories():
    """テンプレートカテゴリ一覧を取得"""
    return list(PHARMA_SEARCH_TEMPLATES.keys())


def get_templates_by_category(category):
    """指定カテゴリのテンプレート一覧を取得"""
    if category in PHARMA_SEARCH_TEMPLATES:
        return PHARMA_SEARCH_TEMPLATES[category]["templates"]
    return []


def get_all_templates():
    """全テンプレートをフラットなリストで取得"""
    all_templates = []
    for category_data in PHARMA_SEARCH_TEMPLATES.values():
        all_templates.extend(category_data["templates"])
    return all_templates


def search_templates(keyword):
    """キーワードでテンプレートを検索"""
    matching_templates = []
    keyword_lower = keyword.lower()

    for category, data in PHARMA_SEARCH_TEMPLATES.items():
        # カテゴリ名での検索
        if keyword_lower in category.lower() or keyword_lower in data["title"].lower():
            matching_templates.extend([(template, category) for template in data["templates"]])
        else:
            # テンプレート内容での検索
            for template in data["templates"]:
                if keyword_lower in template.lower():
                    matching_templates.append((template, category))

    return matching_templates
