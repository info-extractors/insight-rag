"""Unit tests for GuardrailEngine and RAGEvaluator."""

from src.ingestion.chunker import Chunk
from src.retrieval.hybrid import ScoredChunk
from src.generation.guardrails import GuardrailEngine
from src.evaluation.metrics import RAGEvaluator


def test_guardrails_pass_with_verified_citations():
    chunk = Chunk(
        chunk_id="chunk_1",
        doc_id="report_fy24",
        content="Free cash flow for FY2024 was $6.4 billion, reflecting 82% cash conversion rate.",
        page_number=3,
        chunk_type="text",
        metadata={"source_file": "report_fy24.pdf"}
    )
    scored = ScoredChunk(chunk=chunk, rrf_score=0.03)

    answer = "Free cash flow reached $6.4 billion in FY2024 with 82% conversion. [Doc: report_fy24.pdf, Page: 3]"

    guardrail = GuardrailEngine()
    result = guardrail.evaluate(answer, [scored])

    assert result.passed is True
    assert result.faithfulness_score > 0.8
    assert result.verified_citations == 1
    assert result.unverified_citations == 0
    assert len(result.hallucinated_numbers) == 0


def test_guardrails_detect_hallucinated_numbers():
    chunk = Chunk(
        chunk_id="chunk_1",
        doc_id="report_fy24",
        content="Operating income reached $7.8 billion.",
        page_number=1,
        chunk_type="text",
        metadata={"source_file": "report_fy24.pdf"}
    )
    scored = ScoredChunk(chunk=chunk, rrf_score=0.03)

    # Injected false metric: $99.9 billion
    hallucinated_answer = "Operating income reached $99.9 billion. [Doc: report_fy24.pdf, Page: 1]"

    guardrail = GuardrailEngine()
    result = guardrail.evaluate(hallucinated_answer, [scored])

    assert "$99.9" in result.hallucinated_numbers or "99.9" in result.hallucinated_numbers
    assert len(result.warnings) > 0


def test_rag_evaluator_metrics():
    chunk = Chunk(
        chunk_id="chunk_1",
        doc_id="report_fy24",
        content="R&D expenditure reached $5.1 billion, representing 18% of total revenue.",
        page_number=2,
        chunk_type="text",
        metadata={"source_file": "report_fy24.pdf"}
    )
    scored = ScoredChunk(chunk=chunk, rrf_score=0.03)

    evaluator = RAGEvaluator()
    report = evaluator.evaluate_turn(
        query="What was the R&D expenditure?",
        retrieved_chunks=[scored],
        answer="R&D expenditure was $5.1 billion.",
        faithfulness_score=1.0
    )

    assert report.context_relevance > 0.0
    assert report.groundedness == 1.0
    assert report.composite_rag_score > 0.5

