import dspy


class GenerateDetailedTopics(dspy.Signature):
    """あなたは日本の法令に詳しい専門家です。下記のクエリー（query）に関係する法令情報を過不足なく収集するにはどんな観点（topic）を調べればよいでしょうか？
    調べるべき観点をブレークダウンし、下記のフォーマットでリストアップしてください。
    各トピックはそれぞれ独立に調査するので、self-containedであるようにし、コンテキストが欠落しないよう気をつけてください。
    また、各トピックは専門知識がなくても内容がわかるように、高校生でもわかるように噛み砕いてください。
    また、ある程度排他的であるほうが好ましいです。
    - topic 1
    - topic 2
    ...
    - topic n
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
