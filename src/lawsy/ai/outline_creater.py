import re

import dspy
from pydantic import BaseModel


class CreateOutline(dspy.Signature):
    """あなたは日本の法令に精通したニュースに敏感な専門家です。収集された情報源をもとに、下記のクエリに対するレポートとして適切なアウトラインを作成してください。
    また、最後にレポートのタイトルを作成してください。結論パートは絶対に作成しないでください。
    アウトラインは以下のMarkdownフォーマットに従って作成し、次のルールを厳守すること。

    1. Queryに法令観点で回答・解説することを目的とした構成にする。
    2. "# Title" をレポートのタイトルに用いる。
    3. "## Title" をセクションのタイトルとして用いる
       - 各セクション ("## Title") に対して、必ず2～3個以上のサブセクション ("### Title") を生成
       - サブセクションの数は多いほどいいので、収集された情報源と引用番号（[4][27]）をできるだけ多く取り込むこと
       - 条文を列挙する等の回答がいいと判断できる場合、サブセクションは5～10個以上作成、多くの種類の条文を使用すること
       - サブセクションの内容が似る場合は統合し、他の内容のサブセクションを設けること
       - サブセクションの引用番号が他と被る場合も統合し、他の内容のサブセクションを設けること
       - 必要に応じて、さらに下位の階層も同様に2つ以上生成すること。
       - セクションとサブセクションには条文を含めないなど、簡潔なタイトルにすること
    4. 今後必要となるので、"### Title"のサブセクションタイトル作成の際には参照した条文の引用番号を記載。引用番号はサブセクションの次の行に記載すること。
       - "### Title [3][4]" のように同じ行に引用番号を記載しないでください
    5. "#### Title"というサブサブセクションは作成しないこと
    6. "## 結論"という結論パートは絶対に作成してはいけない
    7. 出力には "# Title", "## Title"、"### Title"、"#### Title" などのMarkdown形式のタイトル以外のテキストを一切含めないこと。
       - ナンバリングは不要
    8. "#", "##", "###" の階層のみ作成すること

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

    【不適切な出力例】
    # レポートタイトル: xxx    // 「レポートタイトル: 」という修飾はNG
    ## セクション1
    ### サブセクション1 [4]    // 引用はサブセクションの行にはつけない
    [4]
    ### サブセクション2 [30][28[1][27]    // 同上
    [30][28][1][27]
    ## セクション2
    [2][24][29][11][4]    // セクション自体に引用がついている
    ### サブセクション1
    ### サブセクション: yyy    // 「サブセクション: 」という修飾はNG
    [2][24]
    ### サブセクション3
    [29][11][4]
    """  # noqa: E501

    query = dspy.InputField(desc="クエリー", format=str)
    references = dspy.InputField(desc="収集された情報源と引用番号", format=str)
    outline = dspy.OutputField(desc="レポートのアウトライン", format=str)


class FixOutline(dspy.Signature):
    """あなたは仕事の正確性に定評のあるアシスタントです。
    収集したナレッジをもとに法令解説文書のアウトラインを作ったのですが、一部、下記のアウトライン作成ルールを逸脱している可能性があります。
    下記のルールを守るように修正してください。

    1. "# Title" をレポートのタイトルに用いる。
    2. "## Title" をセクションのタイトルとして用いる
       - 各セクション ("## Title") に対して、必ず2～3個以上のサブセクション ("### Title") を生成
       - サブセクションの数は多いほどいいので、収集された情報源と引用番号（[4][27]）をできるだけ多く取り込むこと
       - 条文を列挙する等の回答がいいと判断できる場合、サブセクションは5～10個以上作成、多くの種類の条文を使用すること
       - サブセクションの内容が似る場合は統合し、他の内容のサブセクションを設けること
       - サブセクションの引用番号が他と被る場合も統合し、他の内容のサブセクションを設けること
       - 必要に応じて、さらに下位の階層も同様に2つ以上生成すること。
       - セクションとサブセクションには条文を含めないなど、簡潔なタイトルにすること
    3. 今後必要となるので、"### Title"のサブセクションタイトル作成の際には参照した条文の引用番号を記載。引用番号はサブセクションの次の行に記載すること。
       - "### Title [3][4]" のように同じ行に引用番号を記載しないでください
    4. "#### Title"というサブサブセクションは作成しないこと
    5. "## 結論"という結論パートは絶対に作成してはいけない
    6. 出力には "# Title", "## Title"、"### Title"、"#### Title" などのMarkdown形式のタイトル以外のテキストを一切含めないこと。
       - ナンバリングは不要
    7. "#", "##", "###" の階層のみ作成すること

    【修正が必要な入力アウトライン例】

    ```
    # レポートタイトル: xxx    // 「レポートタイトル:」のような修飾は不要
    ## セクション1
    ### サブセクション1 [4]    // サブセクションと同じ行に引用を書かない
    [4]
    ### サブセクション2 [30][28[1][27]  // サブセクションと同じ行に引用を書かない
    [30][28][1][27]
    ## セクション2
    [2][24][29][11][4]    // セクションには引用をつけない
    ### サブセクション1
    ### サブセクション: yyy    // 「サブセクション:」のような修飾は不要
    [2]
    [24]    // 複数行にわたって引用を書かない
    ### サブセクション3
    [29][11][4]
    ```

    【修正済みアウトライン例】

    ```
    # xxx
    ## セクション1
    ### サブセクション1
    [4]
    ### サブセクション2
    [30][28][1][27]
    ## セクション2
    ### サブセクション1
    [14][25][9]
    ### yyy
    [2][24]
    ### サブセクション3
    [29][11][4]
    ```
    """  # noqa: E501

    outline = dspy.InputField(desc="入力アウトライン", foramt=str)
    fixed_outline = dspy.OutputField(desc="修正済みアウトライン", format=str)


class SubsectionOutline(BaseModel):
    title: str
    reference_ids: list[int]

    def to_text(self) -> str:
        return "\n".join(
            ["### " + self.title, "".join([f"[{reference_id}]" for reference_id in self.reference_ids])]
        ).strip()


class SectionOutline(BaseModel):
    title: str
    subsection_outlines: list[SubsectionOutline]

    def to_text(self) -> str:
        return "\n".join(
            ["## " + self.title] + [subsection_outline.to_text() for subsection_outline in self.subsection_outlines]
        )


class Outline(BaseModel):
    title: str
    section_outlines: list[SectionOutline]

    def to_text(self) -> str:
        return "\n".join(
            ["# " + self.title] + [section_outline.to_text() for section_outline in self.section_outlines]
        )


class OutlineCreater(dspy.Module):
    def __init__(self, lm) -> None:
        self.lm = lm
        self.gen_outline = dspy.Predict(CreateOutline)
        self.fix_outline = dspy.Predict(FixOutline)

    @staticmethod
    def __parse_outline(outline) -> Outline:
        report_title = None
        section_title = None
        subsection_title = None
        section_outlines = []
        subsection_outlines = []
        reference_ids = []
        for line in outline.splitlines():
            if not line.strip():
                continue
            elif line.startswith("# "):
                assert report_title is None
                report_title = line[2:].strip()
                continue
            elif line.startswith("## "):
                if section_title is not None:
                    assert len(subsection_outlines) > 0
                    section_outlines.append(
                        SectionOutline(title=section_title, subsection_outlines=subsection_outlines)
                    )  # noqa: E501
                section_title = line[3:].strip()
                subsection_outlines = []
                continue
            elif line.startswith("### "):
                if subsection_title is not None:
                    subsection_outlines.append(SubsectionOutline(title=subsection_title, reference_ids=reference_ids))
                subsection_title = line[4:].strip()
                reference_ids = []
                continue
            else:
                assert subsection_title is not None
                assert re.match(r"\[\d+\]+", line)
                reference_ids = [int(matched) for matched in re.findall(r"\[(\d+)\]", line)]
                subsection_outlines.append(SubsectionOutline(title=subsection_title, reference_ids=reference_ids))
                subsection_title = None
                reference_ids = []
                continue
        if subsection_title:
            assert section_title is not None
            subsection_outlines.append(SubsectionOutline(title=subsection_title, reference_ids=reference_ids))
            section_outlines.append(SectionOutline(title=section_title, subsection_outlines=subsection_outlines))
        assert report_title is not None
        return Outline(title=report_title, section_outlines=section_outlines)

    def forward(self, query: str, topics: list, references: list[str]) -> dspy.Prediction:
        topics_text = "\n".join([f"- {topic}" for topic in topics])
        references_text = "\n\n".join(references)
        with dspy.settings.context(lm=self.lm):
            create_outline_result = self.gen_outline(
                query=query,
                topics=topics_text,
                references=references_text,
            )
            fix_outline_result = self.fix_outline(outline=create_outline_result.outline)
        parsed_outline = self.__parse_outline(fix_outline_result.fixed_outline)
        return dspy.Prediction(outline=parsed_outline)
