import re

def show_header_html():#ヘッダー作成
    htmls = """
    <div class="mod-header">
    Lawsy
    </div>
    """
    return htmls


def get_hiddenbox_ref_html(i, result):#Reference部を畳んだ表示にする
    html = f"""
    <input type="checkbox" id="toggle{i}" style="display:none;">
    <label for="toggle{i}" class="toggle-label"><span>[{i}] {result.title}</span></label><br>
    <div class="toggle-box">
    <a href="{result.url}">{result.url}</a><br>
    {result.snippet}
    </div>
    """
    return html

def get_reference_tooltip_html(references): #レポート本文中の参照[(番号)]に埋め込むtooltipのリストを返す
    tooltips = []
    for i, result in enumerate(references, start=1):
        tooltip = f"""
        <b>[{i}] {result.title}</b><br>
        <a href="{result.url}">{result.url}</a><br>
        {result.snippet}
        """
        tooltips.append(tooltip)

    return tooltips


def embed_tooltips(text,tooltips):
    # 正規表現パターン: [] 内の数字を抽出
    pattern = r'\[(\d+)\]'
    matches = list(re.finditer(pattern, text))
    
    ret = text
    result = []
    for match in reversed(matches):
        number = int(match.group(1))
        if number - 1 < len(tooltips):
            rep_html = (
                f'<span class="tooltip">[{number}]'
                f'<span class="tooltiptext"><span class="tooltip-header"></span>'
                f'<span class="tooltip-content">{tooltips[number-1]}</span></span></span>'
            )
            ret = ret[:match.start()] + rep_html + ret[match.end():]  # 直接文字列を置換
    return ret