"""Embed A/B chunks using the already working vinuni/test model environment."""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MODEL = os.environ.get(
    "EMBEDDING_MODEL_PATH",
    r"D:\Tuyen\vinuni\lab\K5-L3A-Day05-Track3-ThoCode\models\embeddinggemma-2",
)
PROGRESS = RESULTS / "progress.json"


def update(stage, done, total, detail):
    percent = round(100 * done / total) if total else 100
    state = {"stage": stage, "done": done, "total": total, "percent": percent, "detail": detail, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    PROGRESS.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"| {stage:<14} | {percent:>3}% | {done:>4}/{total:<4} | {detail} |", flush=True)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    print("| Stage          |   % | Done/Total | Details |", flush=True)
    print("|----------------|----:|-----------:|---------|", flush=True)
    update("Load model", 0, 1, "Loading local EmbeddingGemma; no model download")
    torch.set_num_threads(min(8, os.cpu_count() or 4))
    model = SentenceTransformer(MODEL, local_files_only=True, model_kwargs={"dtype": torch.float32})
    dim = model.get_sentence_embedding_dimension()
    if dim != 768:
        raise ValueError(f"Expected 768-dimensional EmbeddingGemma, got {dim}")
    update("Load model", 1, 1, f"EmbeddingGemma ready ({dim} dimensions)")

    chunks = {}
    for strategy in ("A", "B"):
        chunks[strategy] = json.loads((RESULTS / f"chunks_{strategy}.json").read_text(encoding="utf-8"))
    vectors_by_strategy = {}
    for strategy in ("A", "B"):
        records = chunks[strategy]
        texts = [f"Section: {c['metadata'].get('section','unknown')}\n{c['text']}" for c in records]
        batch_size = 32
        vectors = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        for batch_no, start in enumerate(range(0, len(texts), batch_size), 1):
            block = model.encode_document(texts[start:start + batch_size], normalize_embeddings=True, show_progress_bar=False)
            vectors.extend(np.asarray(block, dtype=np.float32))
            update(f"Embed {strategy}", min(start + len(block), len(texts)), len(texts), f"batch {batch_no}/{total_batches}")
        array = np.asarray(vectors, dtype=np.float32)
        vectors_by_strategy[strategy] = array
        output = RESULTS / f"vectors_{strategy}.npz"
        np.savez_compressed(output, vectors=array, chunk_ids=np.asarray([c["chunk_id"] for c in records]),
                            model=np.asarray(MODEL), dimensions=np.asarray(dim))
        print(f"| Save {strategy:<9} | 100% | {len(array):>4}/{len(records):<4} | {output.relative_to(ROOT)} |", flush=True)

    # C is the B chunk set; its only difference is applying metadata filters at query time.
    (RESULTS / "vectors_C.npz").write_bytes((RESULTS / "vectors_B.npz").read_bytes())
    update("Embed C", 1, 1, "Reuses B vectors; metadata filtering is applied at retrieval")
    summary = {
        "model": MODEL,
        "dimensions": dim,
        "normalization": "L2; cosine-compatible",
        "environment": sys.executable,
        "A": {"chunks": len(chunks["A"]), "vectors": len(vectors_by_strategy["A"]), "file": "results/vectors_A.npz"},
        "B": {"chunks": len(chunks["B"]), "vectors": len(vectors_by_strategy["B"]), "file": "results/vectors_B.npz"},
        "C": {"chunks": len(chunks["B"]), "vectors": len(vectors_by_strategy["B"]), "file": "results/vectors_C.npz", "reuses": "B"},
        "note": "Embeddings are real local model outputs. Chroma insertion is a separate store step.",
    }
    (RESULTS / "embedding_stats.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    update("Complete", 1, 1, "All A/B/C embeddings saved")


if __name__ == "__main__":
    main()
