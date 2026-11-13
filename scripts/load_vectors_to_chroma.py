"""Load the real data.pdf vectors into the persistent A/B/C Chroma collections."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter"))
from src.models import Chunk
from src.store import ChromaStore


def main():
    store = ChromaStore(str(ROOT / "results" / "chroma"))
    print("| Chroma | Progress | Details |", flush=True)
    print("|---|---:|---|", flush=True)
    for strategy in ("A", "B", "C"):
        records = json.loads((ROOT / "results" / f"chunks_{strategy}.json").read_text(encoding="utf-8"))
        vector_file = np.load(ROOT / "results" / f"vectors_{strategy}.npz")
        vectors = vector_file["vectors"].tolist()
        ids = vector_file["chunk_ids"].tolist()
        if ids != [r["chunk_id"] for r in records]:
            raise ValueError(f"Vector IDs do not match chunks for strategy {strategy}")
        chunks = [Chunk(r["chunk_id"], r["document_id"], r["source"], r["page"], r["text"], r["metadata"]) for r in records]
        print(f"| {strategy} | 0% | Replacing {len(chunks)} chunks |", flush=True)
        store.replace(strategy, chunks, vectors)
        collection = store.client.get_collection(f"day06-{strategy.lower()}")
        print(f"| {strategy} | 100% | {collection.count()} vectors stored, cosine distance |", flush=True)
        vector_file.close()
    summary = {
        "backend": "Chroma PersistentClient",
        "path": "results/chroma",
        "metric": "cosine",
        "collections": {s: len(json.loads((ROOT / "results" / f"chunks_{s}.json").read_text(encoding="utf-8"))) for s in ("A", "B", "C")},
        "source": "data/data.pdf",
    }
    (ROOT / "results" / "chroma_stats.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
