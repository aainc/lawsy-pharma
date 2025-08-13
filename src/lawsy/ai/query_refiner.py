import dspy

from lawsy.ai.pharma_query_processor import enhance_pharma_query


class RefineQuery(dspy.Signature):
    """
    あなたは薬事法（医薬品医療機器等法）に精通した優秀な薬事専門家です。
    下記のユーザーのクエリーにたいして、薬事法・薬事規制の観点からの回答を与えてくれそうな簡潔なクエリーを一つ作ってください。
    なお、作成にあたっては下記を守って下さい。

    - 薬事法・薬事規制の観点からの回答を与えてくれそうなクエリーをつくること
    - 薬事専門用語（GMP、GCP、GVP、GPSP、PMDA等）を適切に使用すること
    - あなたの作ったクエリーは可能な限りユーザーが作ったクエリーの意図と過不足なく一致させること
    - クエリーは日本語で作成すること
    - Web検索に最適化すること（薬事関連サイトでの検索を想定）
    - 簡潔であること
    """

    query = dspy.InputField(desc="ユーザーのクエリー", format=str)
    refined_query = dspy.OutputField(desc="あなたの作成したクエリー", format=str)


class QueryRefiner(dspy.Module):
    def __init__(self, lm):
        self.refine_query = dspy.Predict(RefineQuery)
        self.lm = lm

    def forward(self, query: str) -> dspy.Prediction:
        # 薬事専門用語処理を適用
        pharma_enhanced = enhance_pharma_query(query)
        enhanced_query = pharma_enhanced["enhanced_query"]

        with dspy.settings.context(lm=self.lm):
            refine_query_result = self.refine_query(query=enhanced_query)

        return dspy.Prediction(refined_query=refine_query_result.refined_query, pharma_context=pharma_enhanced)
