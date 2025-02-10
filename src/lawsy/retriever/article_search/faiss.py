from pathlib import Path

import numpy as np
import numpy.typing as npt

from lawsy.retriever.search_result import ArticleSearchResult


class FaissHNSWArticleRetriever:
    def __init__(
        self,
        path: Path | str | None = None,
        dim: int | None = None,
        m: int = 16,
    ) -> None:
        assert path is not None or dim is not None
        import json

        import faiss

        assert path is not None or (dim is not None and dim > 0)

        if path is not None:
            path = Path(path)
            self.index = faiss.read_index(str(path / "index.faiss"), faiss.IO_FLAG_MMAP)
            meta_data = []
            with open(path / "meta.jsonl") as fin:
                for line in fin:
                    meta_data.append(json.loads(line))
            self.meta_data = meta_data
        else:
            self.index = faiss.IndexHNSWFlat(dim, m, faiss.METRIC_INNER_PRODUCT)
            self.meta_data = []

    def search(self, vec: npt.NDArray[np.float32], k: int) -> list[ArticleSearchResult]:
        vec = vec / np.linalg.norm(vec)
        cossims, indexs = self.index.search(vec.reshape(1, -1), k=k)  # type: ignore
        results = []
        for i, cossim in zip(indexs[0], cossims[0]):
            meta = self.meta_data[i]
            rev_id = meta["file_name"].split(".")[0]
            law_id = rev_id.split("_")[0]
            title = meta["title"]
            chunk = meta["chunk"]
            anchor = meta["anchor"]
            url = f"https://laws.e-gov.go.jp/law/{law_id}#{anchor}"
            result = ArticleSearchResult(
                law_id=law_id,
                rev_id=rev_id,
                title=title,
                snippet=chunk,
                score=cossim,
                anchor=anchor,
                url=url,
                meta=meta,
            )
            results.append(result)
        return results

    def add(self, vectors: npt.NDArray[np.float32], meta_data: list[dict]) -> None:
        self.index.add(vectors / np.linalg.norm(vectors, axis=1, keepdims=True))  # type: ignore
        self.meta_data.extend(meta_data)

    def save(self, path: Path | str) -> None:
        import json

        import faiss

        path = Path(path)
        assert not path.exists() or path.is_dir()
        path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path / "index.faiss"), faiss.IO_FLAG_MMAP)
        with open(path / "meta.jsonl", "w") as fout:
            for record in self.meta_data:
                print(json.dumps(record, ensure_ascii=False), file=fout)

    @staticmethod
    def create(dim: int, m: int = 16) -> "FaissHNSWArticleRetriever":
        assert dim > 0
        assert m > 0
        return FaissHNSWArticleRetriever(dim=dim, m=m)

    @staticmethod
    def load(path: Path | str) -> "FaissHNSWArticleRetriever":
        return FaissHNSWArticleRetriever(path=path)
