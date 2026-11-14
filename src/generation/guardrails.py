import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set
from src.retrieval.hybrid import ScoredChunk

logger = logging.getLogger(__name__)


@dataclass
class GuardrailResult:
    passed: bool
    faithfulness_score: float
    verified_citations: int
    unverified_citations: int
    hallucinated_numbers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "faithfulness_score": round(self.faithfulness_score, 3),
            "verified_citations": self.verified_citations,
            "unverified_citations": self.unverified_citations,
            "hallucinated_numbers": self.hallucinated_numbers,
            "warnings": self.warnings
        }


class GuardrailEngine:
    """Validates citations against retrieved chunks and flags ungrounded quantitative assertions."""

    def __init__(self):
        # Match citations: [Doc: <filename>, Page: <page_no>] or [Source: ...]
        self.citation_pattern = re.compile(
            r"\[(?:Doc|Source):\s*([^,\]]+)(?:,\s*Page:\s*(\d+))?\]",
            re.IGNORECASE
        )
        # Capture currency, percentages, formatted numbers ($12,450 / 35.3% / 2024)
        self.numeric_pattern = re.compile(
            r"(\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?|\$?\d+(?:\.\d+)?%?|\b\d{4}\b)"
        )

    def evaluate(self, answer: str, context_chunks: List[ScoredChunk]) -> GuardrailResult:
        warnings: List[str] = []

        # 1. Validate citation sources and page references against context chunks
        found_citations = self.citation_pattern.findall(answer)
        valid_sources = {
            sc.chunk.metadata.get("source_file", sc.chunk.doc_id).lower()
            for sc in context_chunks
        }
        valid_pages = {sc.chunk.page_number for sc in context_chunks}

        verified_count = 0
        unverified_count = 0

        for doc_name, page_str in found_citations:
            doc_clean = doc_name.strip().lower()
            doc_matched = any(doc_clean in s or s in doc_clean for s in valid_sources)
            page_matched = True
            if page_str:
                try:
                    page_matched = int(page_str) in valid_pages
                except ValueError:
                    page_matched = False

            if doc_matched and page_matched:
                verified_count += 1
            else:
                unverified_count += 1
                warnings.append(f"Unverified citation: [Doc: {doc_name}, Page: {page_str}]")

        # 2. Cross-reference numeric and financial claims
        full_context = " ".join([c.chunk.content for c in context_chunks])
        context_numbers = set(self.numeric_pattern.findall(full_context))
        answer_numbers = set(self.numeric_pattern.findall(answer))

        # Filter out common low-cardinality index numbers (1, 2, 3)
        flagged_numbers: List[str] = []
        for num in answer_numbers:
            if num in {"1", "2", "3", "4", "5"}:
                continue
            if num not in context_numbers:
                flagged_numbers.append(num)

        if flagged_numbers:
            warnings.append(f"Ungrounded numeric claim(s): {', '.join(flagged_numbers[:5])}")

        # 3. Compute composite faithfulness metric
        total_citations = verified_count + unverified_count
        citation_fidelity = (verified_count / total_citations) if total_citations > 0 else 0.8
        numeric_fidelity = 1.0 - (len(flagged_numbers) / max(1, len(answer_numbers)))
        faithfulness = max(0.0, min(1.0, 0.5 * citation_fidelity + 0.5 * numeric_fidelity))

        passed = faithfulness >= 0.7 and unverified_count == 0

        return GuardrailResult(
            passed=passed,
            faithfulness_score=faithfulness,
            verified_citations=verified_count,
            unverified_citations=unverified_count,
            hallucinated_numbers=flagged_numbers,
            warnings=warnings
        )
