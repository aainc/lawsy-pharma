import numpy as np
import numpy.typing as npt


class OpenAITextEmbedding:
    def __init__(
        self,
        model_name: str = "text-embedding-3-large",
    ) -> None:
        from openai import OpenAI

        assert self.model_name in ("text-embedding-3-large", "text-embedding-3-small")
        self.model_name = model_name
        self.client = OpenAI()

    def get_dimension(self) -> int:
        if self.model_name == "text-embedding-3-large":
            return 3072
        else:
            return 1536

    def get_name(self) -> str:
        return f"OpenAI-{self.model_name}"

    def get_detailed_instruct(self, task_description: str, query: str) -> str:
        return f"Instruct: {task_description}\nQuery: {query}"

    def _get_embeddings(self, texts: list[str]) -> npt.NDArray[np.float64]:
        texts = [text.replace("\n", " ") for text in texts]
        response = self.client.embeddings.create(input=texts, model=self.model_name)
        result = np.asarray([d.embedding for d in response.data])
        return result

    def get_query_embeddings(
        self, queries: list[str], task_description: str = "Retrieve passages that answer the following query: "
    ) -> npt.NDArray[np.float64]:
        queries = [self.get_detailed_instruct(task_description, query) for query in queries]
        return self._get_embeddings(queries)

    def get_document_embeddings(self, documents: list[str]) -> npt.NDArray[np.float64]:
        return self._get_embeddings(documents)
