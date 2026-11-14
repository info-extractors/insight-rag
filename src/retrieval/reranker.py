import logging
from typing import List
from src.retrieval.hybrid import ScoredChunk
from src.config import settings

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Second-stage re-ranker evaluating full cross-attention between query and candidate text."""

    def __init__(self, model_name: str = settings.RERANKER_MODEL_NAME):
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(self.model_name)
        except (ImportError, Exception) as err:
            logger.debug("CrossEncoder unavailable (%s). Using lexical-semantic rank scoring.", err)
            self.model = None

    def rerank(self, query: str, candidates: List[ScoredChunk], top_k: int = settings.TOP_K_RERANKED) -> List[ScoredChunk]:
        if not candidates:
            return []

        if self.model is not None:
            pairs = [[query, c.chunk.content] for c in candidates]
            scores = self.model.predict(pairs)
            for c, s in zip(candidates, scores):
                c.rerank_score = float(s)
        else:
            # Fallback lexical overlap blended with RRF rank score
            query_terms = set(query.lower().split())
            for c in candidates:
                terms = set(c.chunk.content.lower().split())
                jaccard = len(query_terms & terms) / max(1, len(query_terms | terms))
                c.rerank_score = float(c.rrf_score * 10.0 + jaccard)

        ranked = sorted(candidates, key=lambda x: x.rerank_score or 0.0, reverse=True)
        return ranked[:top_k]
