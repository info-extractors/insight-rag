import logging
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from src.ingestion.chunker import Chunk
from src.config import settings

logger = logging.getLogger(__name__)


class DenseVectorStore:
    """Vector database interface wrapping ChromaDB with local sentence-transformers."""

    def __init__(self, collection_name: str = "insight_rag_docs"):
        self.collection_name = collection_name
        self.model_name = settings.DENSE_MODEL_NAME
        self.model = None
        self.client = None
        self.collection = None
        self._memory_chunks: Dict[str, Chunk] = {}
        self._memory_vectors: Dict[str, np.ndarray] = {}
        self._init_backend()

    def _init_backend(self):
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            # Note: all-MiniLM-L6-v2 provides good speed/accuracy trade-off for CPU workloads
            self.model = SentenceTransformer(self.model_name)
            self.client = chromadb.PersistentClient(path=str(settings.CHROMA_PERSIST_DIR))
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as err:
            logger.debug("ChromaDB/SentenceTransformers unavailable (%s). Falling back to memory index.", err)
            self.client = None
            self.collection = None

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if self.model is not None:
            embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            return embeddings.tolist()

        # Deterministic hashing embedding for testing environments without torch/transformers
        dim = 128
        vectors = []
        for t in texts:
            vec = np.zeros(dim, dtype=np.float32)
            for word in t.lower().split():
                h = abs(hash(word)) % dim
                vec[h] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            vectors.append(vec.tolist())
        return vectors

    def add_chunks(self, chunks: List[Chunk]):
        if not chunks:
            return

        texts = [c.content for c in chunks]
        ids = [c.chunk_id for c in chunks]
        metadatas = [
            {
                "doc_id": c.doc_id,
                "page_number": c.page_number,
                "chunk_type": c.chunk_type,
                "source_file": c.metadata.get("source_file", ""),
            }
            for c in chunks
        ]

        embeddings = self._embed(texts)

        if self.collection is not None:
            self.collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )

        for c, emb in zip(chunks, embeddings):
            self._memory_chunks[c.chunk_id] = c
            self._memory_vectors[c.chunk_id] = np.array(emb, dtype=np.float32)

    def search(self, query: str, top_k: int = settings.TOP_K_RETRIEVAL) -> List[Tuple[Chunk, float]]:
        if not self._memory_chunks:
            return []

        query_emb = self._embed([query])[0]

        if self.collection is not None and self.collection.count() > 0:
            results = self.collection.query(
                query_embeddings=[query_emb],
                n_results=min(top_k, self.collection.count()),
                include=["documents", "metadatas", "distances"]
            )

            hits: List[Tuple[Chunk, float]] = []
            if results and results["ids"] and len(results["ids"][0]) > 0:
                for idx, chunk_id in enumerate(results["ids"][0]):
                    dist = results["distances"][0][idx] if results.get("distances") else 0.5
                    sim = max(0.0, min(1.0, 1.0 - dist))
                    chunk = self._memory_chunks.get(chunk_id)
                    if chunk:
                        hits.append((chunk, float(sim)))
                    else:
                        meta = results["metadatas"][0][idx]
                        doc_text = results["documents"][0][idx]
                        c = Chunk(
                            chunk_id=chunk_id,
                            doc_id=meta.get("doc_id", "unknown"),
                            content=doc_text,
                            page_number=meta.get("page_number", 1),
                            chunk_type=meta.get("chunk_type", "text"),
                            metadata=meta
                        )
                        hits.append((c, float(sim)))
                return hits

        # In-memory cosine search fallback
        q_vec = np.array(query_emb, dtype=np.float32)
        scored: List[Tuple[Chunk, float]] = []
        for c_id, c in self._memory_chunks.items():
            doc_vec = self._memory_vectors[c_id]
            sim = float(np.dot(q_vec, doc_vec) / (np.linalg.norm(q_vec) * np.linalg.norm(doc_vec) + 1e-9))
            scored.append((c, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        if self.collection is not None:
            return self.collection.count()
        return len(self._memory_chunks)

    def reset(self):
        self._memory_chunks.clear()
        self._memory_vectors.clear()
        if self.client is not None:
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception:
                pass
