import argparse
import pickle
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np
import pandas as pd
import requests
import yaml
from tqdm import tqdm


def _normalize_news_item(item: Any) -> List[str]:
    if isinstance(item, list):
        return [str(x).strip() for x in item if str(x).strip()]
    if isinstance(item, str) and item.strip():
        return [item.strip()]
    return []


def _load_embedding_config(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    for key in ("api_key", "model_name", "base_url"):
        if key not in config:
            raise ValueError(f"missing {key} in {path}")
    if not config["api_key"]:
        raise ValueError(f"api_key is empty in {path}")
    return config


def _embed_text(text: str, config: Dict[str, Any], api_key: str) -> np.ndarray:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"input": text, "model": config["model_name"]}
    response = requests.post(
        f"{config['base_url'].rstrip('/')}/embeddings",
        headers=headers,
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return np.asarray(data["data"][0]["embedding"], dtype=np.float32).reshape(1, -1)


def rebuild(input_pkl: Path, output_db: Path, config_path: Path) -> None:
    config = _load_embedding_config(config_path)
    api_key = config["api_key"][0]

    df = pd.read_pickle(input_pkl)
    if "cal_date" not in df.columns or "news" not in df.columns:
        raise ValueError(f"{input_pkl} must contain cal_date and news columns")

    docs: List[str] = []
    metadata: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        cal_date = pd.to_datetime(row["cal_date"]).strftime("%Y-%m-%d")
        for text in _normalize_news_item(row["news"]):
            docs.append(text)
            metadata.append(
                {
                    "datetime": cal_date,
                    "title": "",
                    "content": text,
                    "type": "kr_news",
                    "source": "samsung",
                    "embedding_model": config["model_name"],
                }
            )

    if not docs:
        raise ValueError(f"no news documents found in {input_pkl}")

    embeddings = []
    for text in tqdm(docs, desc=f"Embedding with {config['model_name']}"):
        embeddings.append(_embed_text(text, config, api_key))

    emb = np.vstack(embeddings).astype(np.float32)
    index = faiss.IndexFlatL2(emb.shape[1])
    index.add(emb)

    output_db.mkdir(parents=True, exist_ok=True)
    with open(output_db / "faiss_index.pkl", "wb") as f:
        pickle.dump(index, f)
    with open(output_db / "metadata.pkl", "wb") as f:
        pickle.dump(metadata, f)

    print(f"model={config['model_name']}")
    print(f"documents={len(docs)}")
    print(f"dimension={emb.shape[1]}")
    print(f"index_ntotal={index.ntotal}")
    print(f"saved={output_db}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_pkl", default="data/samsung_news.pkl")
    parser.add_argument("--output_db", default="data/InformationDB_samsung")
    parser.add_argument("--config", default="config/embedding.yaml")
    args = parser.parse_args()

    rebuild(Path(args.input_pkl), Path(args.output_db), Path(args.config))


if __name__ == "__main__":
    main()
