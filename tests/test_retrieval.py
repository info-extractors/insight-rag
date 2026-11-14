"""Unit tests for SparseBM25Index, DenseVectorStore, and HybridRetriever."""

import pytest
from src.ingestion.chunker import Chunk
from src.retrieval.sparse import SparseBM25Index
from src.retrieval.dense import DenseVectorStore
from src.retrieval.hybrid import HybridRetriever


@pytest.fixture
def sample_chunks():
    return [
        Chunk(
            chunk_id="doc1_c1",
            doc_id="doc1",
            content="NovaCorp cloud revenue reached twelve billion dollars with 35% growth in fiscal year 2024.",
            page_number=1,
            chunk_type="text",
            metadata={"source_file": "doc1.txt"}
        ),
        Chunk(
            chunk_id="doc1_c2",
            doc_id="doc1",
            content="Consumer devices and hardware division experienced a 3% contraction due to supply bottlenecks.",
            page_number=2,
            chunk_type="text",
            metadata={"source_file": "doc1.txt"}
        ),
        Chunk(
            chunk_id="doc2_c1",
            doc_id="doc2",
            content="Semiconductor supply chain concentration in Taiwan and South Korea poses critical operational risk.",
            page_number=1,
            chunk_type="text",
            metadata={"source_file": "doc2.txt"}
        ),
    ]


def test_sparse_bm25_search(sample_chunks):
    bm25 = SparseBM25Index()
    bm25.index_chunks(sample_chunks)

    results = bm25.search("cloud revenue fiscal 2024", top_k=2)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert top_chunk.chunk_id == "doc1_c1"
    assert score > 0.0


def test_hybrid_rrf_retrieval(sample_chunks):
    sparse = SparseBM25Index()
    sparse.index_chunks(sample_chunks)

    dense = DenseVectorStore(collection_name="test_col")
    dense.reset()
    dense.add_chunks(sample_chunks)

    retriever = HybridRetriever(dense, sparse, rrf_k=60)
    hits = retriever.retrieve("semiconductor supply chain risks", top_k=2)

    assert len(hits) > 0
    top_hit = hits[0]
    assert top_hit.chunk.chunk_id == "doc2_c1"
    assert top_hit.rrf_score > 0.0

