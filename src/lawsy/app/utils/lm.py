import json
import os
from pathlib import Path

import dspy


def load_lm(model_name: str, **kwargs) -> dspy.LM:
    """
    params:
        model_name (str)  ex. openai/gpt-4o  vertex_ai/gemini-2.0-flash-001 anthropic/claude-3-5-sonnet-latest  gemini/gemini-1.5-pro
    """  # noqa: E501
    kwargs = dict(max_completion_tokens=8192, temperature=0.0, cache=False, **kwargs)
    # Remove max_tokens to avoid conflict with max_completion_tokens
    kwargs.pop('max_tokens', None)
    assert len(model_name.split("/")) == 2
    provider = model_name.split("/")[0]
    if provider == "openai":
        lm = dspy.LM(model_name, api_key=os.environ["OPENAI_API_KEY"], **kwargs)  # type: ignore
    elif provider == "anthropic":
        lm = dspy.LM(model_name, api_key=os.environ["ANTHROPIC_API_KEY"], **kwargs)  # type: ignore
    elif provider == "gemini":
        lm = dspy.LM(model_name, api_key=os.environ["GOOGLE_AI_API_KEY"], **kwargs)  # type: ignore
    elif provider == "vertex_ai":
        sa_file = Path(os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "sa.json")
        if sa_file.exists():
            with open(sa_file) as fin:
                vertex_credentials = json.load(fin)
            vertex_credentials_json = json.dumps(vertex_credentials)
            lm = dspy.LM(model_name, vertex_credentials=vertex_credentials_json, **kwargs)  # type: ignore
        else:
            lm = dspy.LM(model_name, **kwargs)  # type: ignore
    else:
        raise ValueError(f"provider must be one of [openai, anthropic, gemini, vertex_ai] but {provider} was given")
    
    # Remove max_tokens from LM kwargs to avoid conflict with max_completion_tokens
    if hasattr(lm, 'kwargs') and 'max_tokens' in lm.kwargs:
        lm.kwargs.pop('max_tokens', None)
    
    return lm
