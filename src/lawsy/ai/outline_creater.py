import dspy


class CreateOutline(dspy.Signature):
    """あなたは日本の法令に精通した専門家です。収集された情報源をもとに、下記のクエリに対するレポートとして適切なアウトラインを作成してください。
    また、最後にレポートのタイトルを作成してください。結論パートは絶対に作成しないでください。
    アウトラインは以下のMarkdownフォーマットに従って作成し、次のルールを厳守すること。

    1. "## Title" をセクションのタイトルとして用いる
       → 各セクション ("## Title") に対して、必ず2つ以上のサブセクション ("### Title") を生成
       → サブセクションの数は多いほどいいので、収集された情報源と引用番号（[4][27]）をできるだけ取り込むこと。
       → サブセクションの内容が似る場合は統合し、他の内容のサブセクションを設けること
       → 必要に応じて、さらに下位の階層も同様に2つ以上生成すること。
       → セクションとサブセクションには条文を含めないなど、簡潔なタイトルにすること
    2. 今後必要となるので、"### Title"のサブセクションタイトル作成の際には参照した条文の引用番号を記載
    3. "#### Title"というサブサブセクションは作成しないこと
    4. "## 結論"という結論パートは絶対に作成してはいけない
    5. 出力には "## Title"、"### Title"、"#### Title" などのMarkdown形式のタイトル以外のテキストを一切含めないこと。
       ナンバリングは不要

    【出力例】
    # レポートタイトル
    ## セクション1
    ### サブセクション1
    [4]
    ### サブセクション2
    [30][28][1][27]
    ## セクション2
    ### サブセクション1
    [14][25][9]
    ### サブセクション2
    [2][24]
    ### サブセクション3
    [29][11][4]
    ...
    """

    query = dspy.InputField(desc="クエリー", format=str)
    references = dspy.InputField(desc="収集された情報源と引用番号", format=str)
    outline = dspy.OutputField(desc="レポートのアウトライン", format=str)


class OutlineCreater(dspy.Module):
    def __init__(self, lm) -> None:
        self.lm = lm
        self.gen_outline = dspy.Predict(CreateOutline)

    def forward(self, query: str, topics: list, references: list[str]) -> dspy.Prediction:
        topics_text = "\n".join([f"- {topic}" for topic in topics])
        references_text = "\n\n".join(references)
        with dspy.settings.context(lm=self.lm):
            create_outline_result = self.gen_outline(
                query=query,
                topics=topics_text,
                references=references_text,
            )
        return create_outline_result
