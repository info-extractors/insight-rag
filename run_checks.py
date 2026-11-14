"""System verification script for InsightRAG components."""

import sys
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import settings
from src.ingestion.parser import DocumentParser
from src.ingestion.chunker import DocumentChunker, Chunk
from src.retrieval.sparse import SparseBM25Index
from src.retrieval.dense import DenseVectorStore
from src.retrieval.hybrid import HybridRetriever, ScoredChunk
from src.retrieval.reranker import CrossEncoderReranker
from src.generation.guardrails import GuardrailEngine
from src.evaluation.metrics import RAGEvaluator
from src.app.pipeline import InsightRAGPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("system_check")


def report(step: int, title: str, passed: bool, info: str = ""):
    tag = "[PASS]" if passed else "[FAIL]"
    print(f"{tag} Step {step}: {title}")
    if info:
        print(f"       {info}")


def run_checks():
    print("-" * 65)
    print("InsightRAG System Verification")
    print("-" * 65)

    all_passed = True

    # Step 1: Config
    try:
        assert settings.APP_NAME == "InsightRAG"
        assert settings.DATA_DIR.exists()
        report(1, "Config & Paths", True, f"Base: {settings.BASE_DIR}")
    except Exception as e:
        report(1, "Config & Paths", False, str(e))
        all_passed = False

    # Step 2: Document parsing & table geometry
    try:
        sample_path = settings.SAMPLE_DOCS_DIR / "novacorp_annual_report_fy2024.md"
        assert sample_path.exists(), f"Sample doc missing at {sample_path}"

        parser = DocumentParser()
        doc = parser.parse(sample_path)
        tables = [b for b in doc.blocks if b.block_type == "table"]

        assert len(doc.blocks) >= 4
        assert len(tables) >= 1
        assert "FY2024 Revenue" in tables[0].content
        report(2, "Parser & Table Extraction", True, f"{len(doc.blocks)} blocks, {len(tables)} tables")
    except Exception as e:
        report(2, "Parser & Table Extraction", False, str(e))
        all_passed = False

    # Step 3: Chunking
    try:
        chunker = DocumentChunker(chunk_size=250, chunk_overlap=50)
        chunks = chunker.chunk_document(doc)
        table_chunks = [c for c in chunks if c.chunk_type == "table"]

        assert len(chunks) >= 4
        assert len(table_chunks) >= 1
        report(3, "Hierarchical Chunking", True, f"{len(chunks)} chunks produced")
    except Exception as e:
        report(3, "Hierarchical Chunking", False, str(e))
        all_passed = False

    # Step 4: BM25 index
    try:
        sparse = SparseBM25Index()
        sparse.index_chunks(chunks)
        res = sparse.search("NovaCloud AI Clusters GPU compute", top_k=2)

        assert len(res) > 0
        top_c, sc = res[0]
        assert sc > 0.0
        report(4, "BM25 Sparse Index", True, f"Top score: {sc:.3f} ({top_c.chunk_id})")
    except Exception as e:
        report(4, "BM25 Sparse Index", False, str(e))
        all_passed = False

    # Step 5: Dense vector store
    try:
        dense = DenseVectorStore(collection_name="check_col")
        dense.reset()
        dense.add_chunks(chunks)
        hits = dense.search("operating margin growth and EPS", top_k=2)

        assert len(hits) > 0
        top_d, sim = hits[0]
        assert sim > 0.0
        report(5, "Dense Vector Index", True, f"Similarity: {sim:.3f} across {dense.count()} vectors")
    except Exception as e:
        report(5, "Dense Vector Index", False, str(e))
        all_passed = False

    # Step 6: Hybrid RRF & Reranker
    try:
        retriever = HybridRetriever(dense, sparse, rrf_k=60)
        candidates = retriever.retrieve("cloud infrastructure revenue and semiconductor risks", top_k=5)

        assert len(candidates) > 0
        assert candidates[0].rrf_score > 0.0

        reranker = CrossEncoderReranker()
        top_reranked = reranker.rerank("cloud infrastructure revenue", candidates, top_k=2)
        assert len(top_reranked) == 2
        report(6, "Hybrid RRF & Cross-Encoder", True, f"Top RRF: {candidates[0].rrf_score:.4f}")
    except Exception as e:
        report(6, "Hybrid RRF & Cross-Encoder", False, str(e))
        all_passed = False

    # Step 7: Guardrails
    try:
        guardrail = GuardrailEngine()
        test_chunk = Chunk(
            chunk_id="chk_val_1",
            doc_id="novacorp_annual_report_fy2024",
            content="Cloud Infrastructure & AI revenue reached $12,450 million in FY2024 with 35.3% growth.",
            page_number=1,
            chunk_type="table",
            metadata={"source_file": "novacorp_annual_report_fy2024.md"}
        )
        scored_val = [ScoredChunk(chunk=test_chunk, rrf_score=0.04)]

        test_answer = (
            "Cloud Infrastructure & AI revenue reached $12,450 million with 35.3% growth. "
            "[Doc: novacorp_annual_report_fy2024.md, Page: 1]"
        )
        guard_res = guardrail.evaluate(test_answer, scored_val)

        assert guard_res.passed is True
        assert guard_res.verified_citations == 1
        assert len(guard_res.hallucinated_numbers) == 0

        # Verify detection of invalid numeric assertions
        bad_answer = "Operating margin was $999 billion. [Doc: novacorp_annual_report_fy2024.md, Page: 1]"
        bad_guard_res = guardrail.evaluate(bad_answer, scored_val)
        assert len(bad_guard_res.hallucinated_numbers) > 0

        report(7, "Guardrail Verification", True, f"Faithfulness: {guard_res.faithfulness_score:.1%}")
    except Exception as e:
        report(7, "Guardrail Verification", False, str(e))
        all_passed = False

    # Step 8: End-to-end pipeline
    try:
        pipeline = InsightRAGPipeline()
        ingest_res = pipeline.ingest_file(sample_path)
        assert ingest_res["status"] == "success"

        query_text = "What was the total Cloud revenue in FY2024 and operating margin?"
        response = pipeline.query(query_text, top_k_candidates=5, top_k_final=2)

        assert len(response.answer) > 0
        assert len(response.citations) > 0
        assert response.total_latency_ms > 0.0
        assert response.guardrail["passed"] is True

        report(8, "Pipeline Execution", True, f"Latency: {response.total_latency_ms:.1f}ms, Score: {response.evaluation['composite_rag_score']:.1%}")
    except Exception as e:
        report(8, "Pipeline Execution", False, str(e))
        all_passed = False

    print("-" * 65)
    if all_passed:
        print("Status: All 8 component checks passed successfully.")
    else:
        print("Status: Some component checks failed. Review details above.")
    print("-" * 65)


if __name__ == "__main__":
    run_checks()
