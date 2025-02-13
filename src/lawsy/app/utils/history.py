import json
import os
from typing import Annotated, Union

from google.cloud import storage
from pydantic import BaseModel, ConfigDict

from lawsy.retriever.search_result import ArticleSearchResult, WebSearchResult, to_search_result

SearchResultType = Annotated[Union[ArticleSearchResult, WebSearchResult], ...]


class Report(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # これを追加
    id: str
    timestamp: float
    query: str
    topics: list[str]
    title: str
    report_content: str
    mindmap: str
    references: list[SearchResultType]

    @staticmethod
    def from_dict(d: dict) -> "Report":
        d = d.copy()
        references = [to_search_result(dd) for dd in d.pop("references")]
        return Report(**d, references=references)

    def to_dict(self) -> dict:
        return dict(
            id=self.id,
            timestamp=self.timestamp,
            query=self.query,
            topics=self.topics,
            title=self.title,
            report_content=self.report_content,
            mindmap=self.mindmap,
            references=[reference.model_dump(mode="json") for reference in self.references],
        )

    def save(self, user_id: str) -> None:
        history = [self] + get_history(user_id)
        client = get_storage_client()
        bucket = client.bucket(os.environ["HISTORY_BUCKET_NAME"])
        blob = bucket.blob(f"{user_id}.json")
        json_data = json.dumps([report.to_dict() for report in history], ensure_ascii=False)
        blob.upload_from_string(json_data, content_type="text/json")


def get_storage_client() -> storage.Client:
    client = storage.Client.from_service_account_json("sa.json")
    return client


def get_history(user_id: str) -> list[Report]:
    client = get_storage_client()
    bucket = client.bucket(os.environ["HISTORY_BUCKET_NAME"])
    blob = bucket.blob(f"{user_id}.json")
    if blob.exists():
        with blob.open("r") as fin:
            data = json.load(fin)
        history = [Report.from_dict(d) for d in data]
        return history
    else:
        return []
