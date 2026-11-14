from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from src.ingestion.chunker import Chunk
from src.retrieval.dense import DenseVectorStore
from src.retrieval.sparse import SparseBM25Index
from src.config import settings


@dataclass
class ScoredChunk:
    chunk: Chunk
    rrf_score: float = 0.0
    dense_rank: Optional[int] = None
    dense_score: Optional[float] = None
    sparse_rank: Optional[int] = None
    sparse_score: Optional[float] = None
    rerank_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "doc_id": self.chunk.doc_id,
            "content": self.chunk.content,
            "page_number": self.chunk.page_number,
            "chunk_type": self.chunk.chunk_type,
            "rrf_score": round(self.rrf_score, 5),
            "dense_rank": self.dense_rank,
            "dense_score": round(self.dense_score, 4) if self.dense_score is not None else None,
            "sparse_rank": self.sparse_rank,
            "sparse_score": round(self.sparse_score, 4) if self.sparse_score is not None else None,
            "rerank_score": round(self.rerank_score, 4) if self.rerank_score is not None else None,
            "metadata": self.chunk.metadata,
        }


class HybridRetriever:
    """Combines dense semantic vectors with BM25 inverted index results using Reciprocal Rank Fusion (RRF).

    Reference:
        Cormack, Clarke, and Buettcher (SIGIR 2009).
        RRF_Score(d) = sum(1 / (k + rank_m(d)))
    """

    def __init__(
        self,
        dense_store: DenseVectorStore,
        sparse_index: SparseBM25Index,
        rrf_k: int = settings.RRF_K_CONSTANT,
    ):
        self.dense_store = dense_store
        self.sparse_index = sparse_index
        # k=60 balances high-ranking items across heterogeneous scoring distributions
        self.rrf_k = rrf_k

    def retrieve(self, query: str, top_k: int = settings.TOP_K_RETRIEVAL) -> List[ScoredChunk]:
        # Over-sample candidates before fusion to maximize recall
        candidate_pool_size = max(top_k * 2, 20)
        dense_results = self.dense_store.search(query, top_k=candidate_pool_size)
        sparse_results = self.sparse_index.search(query, top_k=candidate_pool_size)

        candidates: Dict[str, ScoredChunk] = {}

        for rank, (chunk, score) in enumerate(dense_results, start=1):
            cid = chunk.chunk_id
            if cid not in candidates:
                candidates[cid] = ScoredChunk(chunk=chunk)
            candidates[cid].dense_rank = rank
            candidates[cid].dense_score = score
            candidates[cid].rrf_score += 1.0 / (self.rrf_k + rank)

        for rank, (chunk, score) in enumerate(sparse_results, start=1):
            cid = chunk.chunk_id
            if cid not in candidates:
                candidates[cid] = ScoredChunk(chunk=chunk)
            candidates[cid].sparse_rank = rank
            candidates[cid].sparse_score = score
            candidates[cid].rrf_score += 1.0 / (self.rrf_k + rank)

        fused = sorted(candidates.values(), key=lambda item: item.rrf_score, reverse=True)
        return fused[:top_k]
