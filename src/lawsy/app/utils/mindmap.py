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
    num_subheaders = len([line for line in mindmap.split("\n") if line.startswith("### ")])
    height = num_subheaders * 25
    return markmap(data, height=height)
