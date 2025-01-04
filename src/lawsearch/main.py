from pathlib import Path

import typer

app = typer.Typer()


@app.command()
def extract_law_texts(xml_dir: Path, output_jsonl_file: Path) -> None:
    import json

    from lxml import etree
    from tqdm import tqdm

    def _add_text(texts: list[str], element: etree._Element) -> None:
        if element.text:
            texts.append(element.text)
        for child in element:
            _add_text(texts, child)
        if element.tail:
            texts.append(element.tail)

    def get_text(element: etree._Element) -> str:
        texts = []
        _add_text(texts, element)
        return "".join(texts)

    output_jsonl_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_jsonl_file, "w") as fout:
        xml_files = list(xml_dir.glob("**/*.xml"))
        for xml_file in tqdm(xml_files):
            tree = etree.parse(xml_file)
            root = tree.getroot()
            num = root.find("LawNum").text  # type: ignore
            title = root.find("LawBody/LawTitle").text  # type: ignore
            text = get_text(root)
            print(
                json.dumps(
                    {"file_name": xml_file.name, "law_num": num, "law_title": title, "text": text}, ensure_ascii=False
                ),
                file=fout,
            )


@app.command()
def embed_law_texts(input_jsonl_file: Path, output_jsonl_file: Path) -> None:
    import json

    from tqdm import tqdm

    from lawsearch.encoder.me5 import ME5Instruct

    encoder = ME5Instruct()
    with open(input_jsonl_file) as fin, open(output_jsonl_file, "w") as fout:
        for line in tqdm(fin):
            d = json.loads(line)
            text = d["text"]
            if text.strip() == "":
                continue
            embedding = encoder.get_document_embeddings([text])[0]
            print(
                json.dumps({"file_name": d["file_name"], "embedding": embedding.tolist()}, ensure_ascii=False),
                file=fout,
            )


@app.command()
def create_law_index(input_jsonl_file: Path, output_db_path: Path, collection_name: str = "law_collection") -> None:
    import json

    import numpy as np
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams
    from tqdm import tqdm

    client = QdrantClient(path=str(output_db_path))
    with open(input_jsonl_file) as fin:
        points = []
        embeddings = []
        metas = []
        for i, line in tqdm(enumerate(fin)):
            d = json.loads(line)
            embeddings.append(d["embedding"])
            metas.append({"file_name": d["file_name"]})
            point = PointStruct(
                id=i,
                vector=np.asarray(d["embedding"]).tolist(),  # type: ignore
                payload={"file_name": d["file_name"]},
            )
            points.append(point)
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=len(points[0].vector), distance=Distance.COSINE),
        )
    client.upsert(collection_name, points)


if __name__ == "__main__":
    app()
