def show_header_html():
    htmls = """
    <div class="mod-header">
    Lawsy
    </div>
    """
    return htmls


def get_hiddenbox_ref_html(i, result):
    html = f"""
    <input type="checkbox" id="toggle{i}" style="display:none;">
    <label for="toggle{i}" class="toggle-label"><span>[{i}] {result.title}</span></label><br>
    <div class="toggle-box">
    <a href="{result.url}">{result.url}</a><br>
    {result.snippet}
    </div>
    """
    return html
