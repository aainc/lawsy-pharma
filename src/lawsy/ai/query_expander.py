import dspy


class GenerateDetailedTopics(dspy.Signature):
    """あなたは日本の法令に精通した専門家です。
    下記のクエリー（query）に関係する法令情報を過不足なく収集するために必要な検索トピックを具体的かつ法令用語に即した形でリストアップしてください。
    検索はベクトル検索として使用されますなお、条件は以下の通りです：
    - クエリーのうち、ユーザーが回答を求める部分にフォーカスしてください。前提部分等はあまりフォーカスしなくていい
    - 一般的な用語は法令での専門用語を優先。法令用語が含まれていない場合は、該当しそうな法令用語や関連用語を補完
    - 調査トピックは独立しており、互いに重複せず、個別に調査可能な形にしてください
    - 調査項目は法令コーパスに適した具体的なトピックとしてください（短文または具体的な法令用語）
    - 出力は検索精度を高めるため、法令での使用が想定される具体的な専門用語や関連する条文番号を含めてください
    - トピックはナンバリングする必要はなく、トピックの内容のみ記載して下さい
    - トピックの個数は多くてもせいぜい20個までにしてください。多ければよいというわけではないです。
    - トピックは **self-contained** で、もとのクエリーに関連したものであることが保証されたものにしてください

    出力フォーマット：
    - xxx
    - yyy
    - ...
    - zzz

    """

    query = dspy.InputField(desc="query", format=str)
    topics = dspy.OutputField(desc="topics", format=str)


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

    def forward(self, query: str) -> dspy.Prediction:
        with dspy.settings.context(lm=self.lm):
            generate_detailed_topics_result = self.generate_detailed_topics(query=query)
            topics = [cleanse_topic(topic) for topic in generate_detailed_topics_result.topics.split("\n")]
            topics = [topic for topic in topics if topic]
        return dspy.Prediction(topics=topics)
