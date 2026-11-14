"""Integration test for the full end-to-end InsightRAGPipeline."""

from pathlib import Path
from src.app.pipeline import InsightRAGPipeline
from src.config import settings


def test_end_to_end_pipeline():
    pipeline = InsightRAGPipeline()

    sample_doc = settings.SAMPLE_DOCS_DIR / "novacorp_annual_report_fy2024.md"
    assert sample_doc.exists(), "Sample doc must exist for pipeline testing"

    # 1. Ingestion
    ingest_result = pipeline.ingest_file(sample_doc)
    assert ingest_result["status"] == "success"
    assert ingest_result["chunks_indexed"] > 0

    # 2. Query
    query = "What was the total consolidated revenue in FY2024?"
    response = pipeline.query(query, top_k_candidates=5, top_k_final=2)

    assert response.query == query
    assert len(response.answer) > 0
    assert len(response.retrieved_chunks) > 0
    assert response.total_latency_ms > 0.0
    assert "guardrail" in response.__dict__
    assert "evaluation" in response.__dict__

