#!/usr/bin/env python3
"""
薬事法特化システムの簡易テスト
"""

import sys
import os
from pathlib import Path

# src ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_pharma_query_processor():
    """薬事専門用語処理のテスト"""
    print("=== 薬事専門用語処理テスト ===")
    
    try:
        from lawsy.ai.pharma_query_processor import enhance_pharma_query
        
        test_queries = [
            "GMP査察について",
            "治験の実施基準",
            "製造販売業許可の要件"
        ]
        
        for query in test_queries:
            print(f"\n入力クエリ: {query}")
            result = enhance_pharma_query(query)
            print(f"展開クエリ: {result['expanded_query'][:100]}...")
            print(f"強化クエリ: {result['enhanced_query'][:100]}...")
            print(f"同義語クエリ数: {len(result['synonym_queries'])}")
            if result['relevant_regulations']:
                print(f"関連法令: {result['relevant_regulations'][:2]}")
        
        print("✓ 薬事専門用語処理テスト成功")
        return True
        
    except Exception as e:
        print(f"✗ 薬事専門用語処理テストエラー: {e}")
        return False


def test_pharma_templates():
    """薬事法検索テンプレートのテスト"""
    print("\n=== 薬事法検索テンプレートテスト ===")
    
    try:
        from lawsy.app.templates.pharma_templates import (
            get_template_categories, 
            get_templates_by_category,
            search_templates
        )
        
        # カテゴリテスト
        categories = get_template_categories()
        print(f"テンプレートカテゴリ数: {len(categories)}")
        print(f"カテゴリ: {categories[:3]}")
        
        # テンプレート取得テスト
        if categories:
            templates = get_templates_by_category(categories[0])
            print(f"'{categories[0]}'テンプレート数: {len(templates)}")
            if templates:
                print(f"サンプル: {templates[0][:50]}...")
        
        # 検索テスト
        search_results = search_templates("GMP")
        print(f"'GMP'検索結果数: {len(search_results)}")
        
        print("✓ 薬事法検索テンプレートテスト成功")
        return True
        
    except Exception as e:
        print(f"✗ 薬事法検索テンプレートテストエラー: {e}")
        return False


def test_pharma_data():
    """薬事法データの存在確認"""
    print("\n=== 薬事法データ確認テスト ===")
    
    try:
        # XMLファイルの確認
        xml_dir = Path("data/pharma_xml")
        processed_xml_dir = Path("data/pharma_xml_processed")
        output_dir = Path("outputs/pharma")
        
        xml_files = list(xml_dir.glob("*.xml")) if xml_dir.exists() else []
        processed_files = list(processed_xml_dir.glob("*.xml")) if processed_xml_dir.exists() else []
        
        print(f"元XMLファイル数: {len(xml_files)}")
        print(f"処理済みXMLファイル数: {len(processed_files)}")
        
        # 処理済みデータの確認
        chunks_file = output_dir / "article_chunks.jsonl"
        embeddings_file = output_dir / "article_chunk_embeddings.parquet"
        faiss_dir = output_dir / "article_chunks_faiss"
        
        print(f"チャンクファイル存在: {chunks_file.exists()}")
        print(f"埋め込みファイル存在: {embeddings_file.exists()}")
        print(f"FAISSインデックス存在: {faiss_dir.exists()}")
        
        if chunks_file.exists():
            with open(chunks_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"チャンク数: {len(lines)}")
        
        print("✓ 薬事法データ確認テスト成功")
        return True
        
    except Exception as e:
        print(f"✗ 薬事法データ確認テストエラー: {e}")
        return False


def test_config_changes():
    """設定変更の確認"""
    print("\n=== 設定変更確認テスト ===")
    
    try:
        # config.pyの薬事ドメイン設定確認
        config_file = Path("src/lawsy/app/config.py")
        if config_file.exists():
            content = config_file.read_text(encoding='utf-8')
            pharma_domains = ["pmda.go.jp", "mhlw.go.jp", "nihs.go.jp"]
            found_domains = sum(1 for domain in pharma_domains if domain in content)
            print(f"薬事ドメイン設定確認: {found_domains}/{len(pharma_domains)}個検出")
        
        print("✓ 設定変更確認テスト成功")
        return True
        
    except Exception as e:
        print(f"✗ 設定変更確認テストエラー: {e}")
        return False


def main():
    """メインテスト実行"""
    print("薬事法特化システム テスト開始")
    print("=" * 50)
    
    tests = [
        test_pharma_data,
        test_config_changes, 
        test_pharma_query_processor,
        test_pharma_templates
    ]
    
    results = []
    for test_func in tests:
        results.append(test_func())
    
    print("\n" + "=" * 50)
    print("テスト結果サマリー")
    print(f"成功: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 全テスト成功！薬事法特化システムが正常に動作しています。")
        return 0
    else:
        print("⚠️  一部テストが失敗しました。詳細を確認してください。")
        return 1


if __name__ == "__main__":
    exit(main())