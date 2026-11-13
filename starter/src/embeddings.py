"""Local EmbeddingGemma 2 vectors with its asymmetric retrieval prompts."""
import os
from pathlib import Path
from typing import Protocol

DEFAULT_MODEL = r'D:\Tuyen\vinuni\lab\K5-L3A-Day05-Track3-ThoCode\models\embeddinggemma-2'

def default_model():
    return os.environ.get('EMBEDDING_MODEL') or DEFAULT_MODEL

class Embedder(Protocol):
    model_name: str
    dimensions: int
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, question: str) -> list[float]: ...

class MyEmbedder:
    def __init__(self, model_name: str | None = None) -> None:
        import os
        import torch
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name or default_model()
        if not Path(self.model_name).is_dir():
            raise FileNotFoundError(f'Không tìm thấy thư mục model embedding: {self.model_name}')
        torch.set_num_threads(min(8, os.cpu_count() or 4))
        self.model = SentenceTransformer(self.model_name, local_files_only=True,
                                         model_kwargs={'dtype': torch.float32})
        self.dimensions = self.model.get_sentence_embedding_dimension()
        if self.dimensions != 768:
            raise ValueError(f'Expected 768-dimensional EmbeddingGemma 2, got {self.dimensions}')

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import numpy as np
        vectors = np.asarray(self.model.encode(texts, prompt_name='Document', batch_size=32, normalize_embeddings=False, show_progress_bar=True), dtype=np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True).clip(min=1e-12)
        return vectors.tolist()

    def embed_query(self, question: str) -> list[float]:
        import numpy as np
        vector = np.asarray(self.model.encode(question, prompt_name='SearchQuery', normalize_embeddings=False), dtype=np.float32)
        vector /= max(float(np.linalg.norm(vector)), 1e-12)
        return vector.tolist()
