import dspy


class WriteReport(dspy.Signature):
    """あなたは法令に関するわかりやすい解説を書くことに定評のある信頼できるライターです。
    下記のクエリーに関する調査をしており、クエリーをもとに生成したトピックに対して情報を収集しました。それをもとに下記のMarkdownフォーマットで事実に基づく解説を書いてください。
    解説は緻密かつ包括的で情報量が多く、情報源に基づいたものであることが望ましいです。関連する話題に関しては、もれなく記載してください。
    内容の信頼性が重要なので、必ず情報源にあたり、下記指示にあるように引用をするのを忘れないで下さい。

    1. "# Title" を解説のタイトルをあらわすのにつかってください。
    2. "## Title" をセクションのタイトルをあらわすのに使ってください。###, ####, ... などは使わないでください。Markdownではないので **xxx** などの余計なマークアップはしないでください。
    3. 解説のタイトルの直後はリード文ではじめ、その後各セクションをつづけてください。
    4. 必ず情報源の情報に基づき記載し、Hullucinationに気をつけること。記載の根拠となりえる参照すべき情報源は "...です[4][1][27]。" "...ます[21][9]。" のように明示してください。その記述に対しての **関連性が高そうな順** に付与してください。
    5. 正しく引用を明示されているほどあなたの解説は高く評価されます。引用なしの創作は論拠が明確でない限り評価されません。
    6. 情報源を解説の末尾に含める必要はありません。
    7. 日本語のですます調で解説を書いてください。
    """  # noqa: E501

    query = dspy.InputField(desc="クエリー", format=str)
    topics = dspy.InputField(desc="クエリーに関連するトピック", format=str)
    references = dspy.InputField(desc="収集された情報源と引用番号", format=str)
    report = dspy.OutputField(desc="情報源を引用しつつ記載されたレポート", format=str)


class ReportWriter(dspy.Module):
    def __init__(self, lm) -> None:
        self.lm = lm
        self.write_report = dspy.Predict(WriteReport)

    def forward(self, query: str, topics: list, references: list[str]) -> dspy.Prediction:
        topics_text = "\n".join([f"- {topic}" for topic in topics])
        references_text = "\n\n".join([s for s in references])
        with dspy.settings.context(lm=self.lm):
            write_report_result = self.write_report(query=query, topics=topics_text, references=references_text)
        return write_report_result
