from typing import Literal, Optional

from pydantic import BaseModel, HttpUrl

SourceType = Literal["article", "web"]


class BaseSearchResult(BaseModel):
    source_type: Optional[SourceType] = None

    # 共通情報
    title: str
    snippet: str
    score: Optional[float] = None
    meta: dict

    def to_dict(self) -> dict:
        return self.model_dump()


class ArticleSearchResult(BaseSearchResult):
    source_type: Optional[SourceType] = "article"
    law_id: str
    rev_id: str  # xxx_xxx_xxx
    anchor: str
    url: HttpUrl | str  # (ugly fix) str is added to prevent https://github.com/pydantic/pydantic/issues/1684


class WebSearchResult(BaseSearchResult):
    source_type: Optional[SourceType] = "web"
    url: HttpUrl | str  # (ugly fix) str is added to prevent https://github.com/pydantic/pydantic/issues/1684

    full_content: Optional[str] = None
