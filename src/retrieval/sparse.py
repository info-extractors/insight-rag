"""Sparse inverted index using Okapi BM25 for precise keyword, acronym, and numerical matching."""

from typing import List, Tuple, Dict, Any
import math
import re
from src.ingestion.chunker import Chunk
from src.config import settings


class SparseBM25Index:
    """Keyword search engine implementing the Okapi BM25 ranking algorithm."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[Chunk] = []
        self.corpus_size: int = 0
        self.avg_doc_len: float = 0.0
        self.doc_lengths: List[int] = []
        self.doc_freqs: Dict[str, int] = {}
        self.term_freqs: List[Dict[str, int]] = []
        self.idf: Dict[str, float] = {}

    def _tokenize(self, text: str) -> List[str]:
        """Lowercases and extracts alpha-numeric tokens."""
        return re.findall(r"\b\w+\b", text.lower())

    def index_chunks(self, chunks: List[Chunk]):
        """Builds inverted index and precomputes IDF weights for all tokens."""
        self.chunks = list(chunks)
        self.corpus_size = len(chunks)
        if self.corpus_size == 0:
            return

        self.doc_lengths = []
        self.doc_freqs = {}
        self.term_freqs = []

        total_length = 0
        for chunk in chunks:
            tokens = self._tokenize(chunk.content)
            self.doc_lengths.append(len(tokens))
            total_length += len(tokens)

            tf: Dict[str, int] = {}
            seen_in_doc = set()
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
                if t not in seen_in_doc:
                    self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1
                    seen_in_doc.add(t)
            self.term_freqs.append(tf)

        self.avg_doc_len = total_length / self.corpus_size

        # Precompute Robertson-Spärck Jones IDF
        self.idf = {}
        for term, df in self.doc_freqs.items():
            self.idf[term] = math.log(1.0 + (self.corpus_size - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = settings.TOP_K_RETRIEVAL) -> List[Tuple[Chunk, float]]:
        """Scores all indexed chunks against query terms using Okapi BM25."""
        if self.corpus_size == 0:
            return []

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        scores: List[float] = [0.0] * self.corpus_size

        for term in q_tokens:
            if term not in self.idf:
                continue
            idf_val = self.idf[term]
            for doc_idx in range(self.corpus_size):
                tf = self.term_freqs[doc_idx].get(term, 0)
                if tf == 0:
                    continue
                doc_len = self.doc_lengths[doc_idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avg_doc_len + 1e-9)))
                scores[doc_idx] += idf_val * (numerator / denominator)

        ranked_indices = sorted(range(self.corpus_size), key=lambda i: scores[i], reverse=True)
        results: List[Tuple[Chunk, float]] = []
        for idx in ranked_indices[:top_k]:
            if scores[idx] > 0.0:
                results.append((self.chunks[idx], float(scores[idx])))

        return results

    def count(self) -> int:
        return self.corpus_size

    def reset(self):
        self.chunks.clear()
        self.corpus_size = 0
        self.doc_lengths.clear()
        self.doc_freqs.clear()
        self.term_freqs.clear()
        self.idf.clear()

