import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

from src.ingestion.parser import DocumentParser, ParsedDocument
from src.ingestion.chunker import DocumentChunker, Chunk
from src.retrieval.dense import DenseVectorStore
from src.retrieval.sparse import SparseBM25Index
from src.retrieval.hybrid import HybridRetriever, ScoredChunk
from src.retrieval.reranker import CrossEncoderReranker
from src.generation.generator import RAGGenerator, GenerationResult
from src.generation.guardrails import GuardrailEngine, GuardrailResult
from src.evaluation.metrics import RAGEvaluator, EvaluationReport
from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QueryResponse:
    query: str
    answer: str
    citations: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    guardrail: Dict[str, Any]
    evaluation: Dict[str, Any]
    latency_breakdown_ms: Dict[str, float]
    total_latency_ms: float


class InsightRAGPipeline:
    """Core orchestration pipeline coordinating ingestion, hybrid search, reranking, and verification."""

    def __init__(self):
        self.parser = DocumentParser()
        self.chunker = DocumentChunker()
        self.dense_store = DenseVectorStore()
        self.sparse_index = SparseBM25Index()
        self.hybrid_retriever = HybridRetriever(self.dense_store, self.sparse_index)
        self.reranker = CrossEncoderReranker()
        self.generator = RAGGenerator()
        self.guardrails = GuardrailEngine()
        self.evaluator = RAGEvaluator()
        self.indexed_documents: List[str] = []

    def ingest_file(self, file_path: str | Path) -> Dict[str, Any]:
        start = time.perf_counter()
        parsed_doc = self.parser.parse(file_path)
        chunks = self.chunker.chunk_document(parsed_doc)

        self.dense_store.add_chunks(chunks)
        self.sparse_index.index_chunks(chunks)

        if parsed_doc.filename not in self.indexed_documents:
            self.indexed_documents.append(parsed_doc.filename)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        logger.info("Ingested %s: %d chunks in %.2f ms", parsed_doc.filename, len(chunks), elapsed_ms)

        return {
            "status": "success",
            "doc_id": parsed_doc.doc_id,
            "filename": parsed_doc.filename,
            "total_pages": parsed_doc.total_pages,
            "blocks_extracted": len(parsed_doc.blocks),
            "chunks_indexed": len(chunks),
            "ingestion_time_ms": round(elapsed_ms, 2)
        }

    def query(
        self,
        text: str,
        top_k_candidates: int = settings.TOP_K_RETRIEVAL,
        top_k_final: int = settings.TOP_K_RERANKED
    ) -> QueryResponse:
        t0 = time.perf_counter()
        timings: Dict[str, float] = {}

        # First stage: Hybrid dense + BM25 retrieval via RRF
        t_start = time.perf_counter()
        candidates = self.hybrid_retriever.retrieve(text, top_k=top_k_candidates)
        timings["hybrid_retrieval_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        # Second stage: Cross-encoder re-ranking
        t_start = time.perf_counter()
        top_chunks = self.reranker.rerank(text, candidates, top_k=top_k_final)
        timings["reranking_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        # Synthesis
        t_start = time.perf_counter()
        gen_result = self.generator.generate(text, top_chunks)
        timings["generation_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        # Guardrails check
        t_start = time.perf_counter()
        guard_result = self.guardrails.evaluate(gen_result.answer, top_chunks)
        timings["guardrails_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        # RAG Triad offline metrics
        t_start = time.perf_counter()
        eval_report = self.evaluator.evaluate_turn(
            query=text,
            retrieved_chunks=top_chunks,
            answer=gen_result.answer,
            faithfulness_score=guard_result.faithfulness_score
        )
        timings["evaluation_ms"] = round((time.perf_counter() - t_start) * 1000.0, 2)

        total_latency = (time.perf_counter() - t0) * 1000.0

        return QueryResponse(
            query=text,
            answer=gen_result.answer,
            citations=[
                {
                    "doc_id": c.doc_id,
                    "page_number": c.page_number,
                    "source_file": c.source_file,
                    "snippet": c.snippet
                }
                for c in gen_result.citations
            ],
            retrieved_chunks=[c.to_dict() for c in top_chunks],
            guardrail=guard_result.to_dict(),
            evaluation=eval_report.to_dict(),
            latency_breakdown_ms=timings,
            total_latency_ms=round(total_latency, 2)
        )

    def stats(self) -> Dict[str, Any]:
        return {
            "dense_vectors_count": self.dense_store.count(),
            "sparse_corpus_size": self.sparse_index.count(),
            "indexed_documents": self.indexed_documents,
            "embedding_model": settings.DENSE_MODEL_NAME,
            "reranker_model": settings.RERANKER_MODEL_NAME,
            "llm_provider": settings.LLM_PROVIDER
        }
