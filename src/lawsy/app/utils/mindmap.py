from streamlit_markmap import markmap


def draw_mindmap(mindmap: str):
    data = f"""
---
markmap:
  pan: false
  zoom: false
---

{mindmap}
"""
    num_headers = len([line for line in mindmap.split("\n") if line.startswith("## ")])
    num_subheaders = len([line for line in mindmap.split("\n") if line.startswith("### ")])
    height = 15 * (num_subheaders + num_headers) + 200
    return markmap(data, height=height)
