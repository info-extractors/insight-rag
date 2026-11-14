"""Automated RAG Triad evaluation metrics: Context Relevance, Groundedness, and Answer Relevance."""

from dataclasses import dataclass
from typing import List, Dict, Any
import re
from src.retrieval.hybrid import ScoredChunk


@dataclass
class EvaluationReport:
    context_relevance: float  # 0.0 to 1.0
    groundedness: float       # 0.0 to 1.0
    answer_relevance: float   # 0.0 to 1.0
    composite_rag_score: float # Harmonic / weighted mean
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_relevance": round(self.context_relevance, 3),
            "groundedness": round(self.groundedness, 3),
            "answer_relevance": round(self.answer_relevance, 3),
            "composite_rag_score": round(self.composite_rag_score, 3),
            "details": self.details
        }


class RAGEvaluator:
    """Evaluates end-to-end RAG pipeline quality using deterministic heuristic metrics."""

    def __init__(self):
        pass

    def evaluate_turn(
        self,
        query: str,
        retrieved_chunks: List[ScoredChunk],
        answer: str,
        faithfulness_score: float = 1.0
    ) -> EvaluationReport:
        """Computes the RAG Triad scores for a single query-answer turn."""
        q_tokens = set(re.findall(r"\b\w{3,}\b", query.lower()))
        a_tokens = set(re.findall(r"\b\w{3,}\b", answer.lower()))

        # 1. Context Relevance: Fraction of retrieved chunks containing query keywords
        relevant_chunks_count = 0
        total_chunks = max(1, len(retrieved_chunks))
        for sc in retrieved_chunks:
            c_tokens = set(re.findall(r"\b\w{3,}\b", sc.chunk.content.lower()))
            overlap = len(q_tokens & c_tokens)
            if overlap >= 1:
                relevant_chunks_count += 1

        context_relevance = relevant_chunks_count / total_chunks

        # 2. Groundedness / Faithfulness (from Guardrail Engine)
        groundedness = max(0.0, min(1.0, faithfulness_score))

        # 3. Answer Relevance: Keyword alignment between answer and question
        if not q_tokens:
            answer_relevance = 1.0
        else:
            q_in_a = len(q_tokens & a_tokens)
            answer_relevance = min(1.0, (q_in_a / len(q_tokens)) * 1.5)

        # Composite Score (Weighted average)
        composite = (0.35 * context_relevance) + (0.45 * groundedness) + (0.20 * answer_relevance)

        return EvaluationReport(
            context_relevance=context_relevance,
            groundedness=groundedness,
            answer_relevance=answer_relevance,
            composite_rag_score=composite,
            details={
                "query_token_count": len(q_tokens),
                "answer_token_count": len(a_tokens),
                "evaluated_chunks": total_chunks,
                "relevant_chunks": relevant_chunks_count
            }
        )

