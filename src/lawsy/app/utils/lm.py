import os
from pathlib import Path

import dspy


def load_lm(model_name: str, **kwargs) -> dspy.LM:
    """
    params:
        model_name (str)  ex. openai/gpt-4o  vertex_ai/gemini-2.0-flush-001
    """
    kwargs = dict(max_tokens=8192, temperature=0.0, cache=False, **kwargs)
    assert len(model_name.split("/")) == 2
    provider = model_name.split("/")[0]
    if provider == "openai":
        return dspy.LM(model_name, api_key=os.environ["OPENAI_API_KEY"], **kwargs)  # type: ignore
    elif provider == "vertex_ai":
        credentials_json = Path("sa.json").read_text()
        return dspy.LM(model_name, credentials=credentials_json, **kwargs)  # type: ignore
    else:
        raise ValueError(f"provider must be one of [openai, vertex_ai] but {provider} was given")
