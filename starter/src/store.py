"""Persistent Chroma cosine vector storage with controlled metadata filtering."""
import json
from typing import Any
from .models import Chunk

class ChromaStore:
    def __init__(self, path: str):
        import chromadb
        self.client = chromadb.PersistentClient(path=path)

    def replace(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors) or not chunks:
            raise ValueError('Chunks and vectors must be nonempty and have equal lengths')
        name = 'day06-' + strategy.lower()
        existing = self.client.list_collections()
        if any((item if isinstance(item, str) else item.name) == name for item in existing):
            self.client.delete_collection(name)
        collection = self.client.create_collection(name, metadata={'hnsw:space': 'cosine'})
        for start in range(0, len(chunks), 100):
            batch = chunks[start:start+100]
            metadatas = []
            for c in batch:
                data = {'document_id': c.document_id, 'source': c.source, 'page': c.page,
                        'extra_json': json.dumps(c.metadata, ensure_ascii=False)}
                # Only explicit, verified metadata is copied into filterable fields.
                for key in ('section', 'year', 'document_type', 'version'):
                    if key in c.metadata: data[key] = c.metadata[key]
                metadatas.append(data)
            collection.add(ids=[c.chunk_id for c in batch], embeddings=vectors[start:start+100],
                           documents=[c.text for c in batch], metadatas=metadatas)

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        collection = self.client.get_collection('day06-' + strategy.lower())
        if not collection.count(): return []
        allowed = {'section', 'year', 'document_type', 'version'}
        if filters and not set(filters).issubset(allowed): raise ValueError('Unsupported metadata filter')
        where = None
        if filters:
            clauses = [{k: {'$eq': v}} for k,v in filters.items()]
            where = clauses[0] if len(clauses) == 1 else {'$and': clauses}
        result = collection.query(query_embeddings=[query_vector], n_results=min(top_k, collection.count()), where=where)
        hits = []
        for id_, text, meta, distance in zip(result['ids'][0], result['documents'][0], result['metadatas'][0], result['distances'][0]):
            extra = json.loads(meta.pop('extra_json'))
            hits.append({'chunk_id': id_, 'text': text, 'score': 1 - distance, **meta, 'metadata': extra})
        return hits
