import dspy

from lawsy.ai.pharma_query_processor import enhance_pharma_query


class GenerateDetailedTopics(dspy.Signature):
    """あなたは日本の薬事法（医薬品医療機器等法）に精通した薬事専門家です。
    下記のクエリーに関して、事前にWeb検索をして簡単に下調べしてあります。
    Web検索結果もふまえ、クエリーに関する薬事法・薬事規制の解説・解釈文書を作成するために必要な法令を検索しようとしています。
    法令検索はセマンティックサーチできるのでキーワード・短文などで検索可能です。

    解説・解釈に必要な薬事関連法令を適切にヒットさせきるための検索トピックを以下の形式でリストアップしてください。

    出力フォーマット：
    - xxx
    - yyy
    - ...
    - zzz

    検索トピックをリストアップするにあたり、以下の条件を遵守してください。

    - クエリーの意味を十分汲み取ること
    - 薬事法・薬事規制に関するクエリーに対する法令解説・解釈を行うのに必要な法令が揃うように検索トピックをリストアップしてください
    - 薬事専門用語（GMP、GCP、GVP、GPSP、製造販売業、治験等）を積極的に使用してください
    - 一般的な用語は薬事法での専門用語を優先してください。薬事法令用語が含まれていない場合は、該当しそうな薬事法令用語や関連用語を補完してください
    - 検索トピックは可能な限り互いに重複せず、個別に調査可能な形にしてください。 **self-contained** であるべきです
    - 検索トピックは薬事法令コーパスに準拠した具体的なものにしてください（短文または具体的な薬事法令用語）
    - 検索精度を高めるため、薬事法での使用が想定される具体的な専門用語や関連する条文番号を含めてください
    - 検索トピックをナンバリングする必要はありません。検索トピックの内容のみ記載してください
    - 検索トピックの個数は多くても10個までにしてください。多ければよいというわけではないです
    """  # noqa: E501

    query = dspy.InputField(desc="クエリー", format=str)
    web_search_results = dspy.InputField(desc="Web検索結果", format=str)
    topics = dspy.OutputField(desc="リストアップされた検索トピック", format=str)


def cleanse_topic(topic: str) -> str:
    if topic.startswith("- "):
        topic = topic[2:].strip()
    if topic.startswith('"') and topic.endswith('"'):
        topic = topic[1:-1].strip()
    topic = topic.strip()
    return topic


class QueryExpander(dspy.Module):
    def __init__(self, lm):
        #        self.generate_detailed_topics = dspy.ChainOfThought(GenerateDetailedTopics)
        self.generate_detailed_topics = dspy.Predict(GenerateDetailedTopics)
        self.lm = lm

    def forward(self, query: str, web_search_results: str) -> dspy.Prediction:
        # 薬事専門用語処理を適用
        pharma_enhanced = enhance_pharma_query(query)
        enhanced_query = pharma_enhanced["enhanced_query"]

        with dspy.settings.context(lm=self.lm):
            generate_detailed_topics_result = self.generate_detailed_topics(
                query=enhanced_query, web_search_results=web_search_results
            )
            topics = [cleanse_topic(topic) for topic in generate_detailed_topics_result.topics.split("\n")]
            topics = [topic for topic in topics if topic]

            # 薬事関連法令情報を追加トピックとして含める
            relevant_regulations = pharma_enhanced["relevant_regulations"]
            for regulation in relevant_regulations[:3]:  # 上位3つまで
                if regulation not in topics:
                    topics.append(regulation)

        return dspy.Prediction(topics=topics, pharma_context=pharma_enhanced)
