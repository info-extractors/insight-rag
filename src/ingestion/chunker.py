"""Hierarchical and layout-aware chunking engine.

Prevents splitting structured tables, maintains sliding context windows for continuous
prose, and attaches rich audit metadata for reliable citation tracking.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from src.ingestion.parser import ParsedDocument, ContentBlock
from src.config import settings


@dataclass
class Chunk:
    """A granular chunk ready for dense embedding and sparse indexing."""
    chunk_id: str
    doc_id: str
    content: str
    page_number: int
    chunk_type: str  # "text" or "table"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "content": self.content,
            "page_number": self.page_number,
            "chunk_type": self.chunk_type,
            "metadata": self.metadata
        }


class DocumentChunker:
    """Splits parsed documents into semantically coherent, metadata-tagged chunks."""

    def __init__(self, chunk_size: int = settings.CHUNK_SIZE, chunk_overlap: int = settings.CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc: ParsedDocument) -> List[Chunk]:
        """Generates a collection of indexed chunks from a ParsedDocument."""
        chunks: List[Chunk] = []
        chunk_counter = 0

        for block in doc.blocks:
            # RULE 1: Never split structured tables across chunk boundaries
            if block.block_type == "table":
                chunk_id = f"{doc.doc_id}_p{block.page_number}_c{chunk_counter}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc.doc_id,
                        content=block.content,
                        page_number=block.page_number,
                        chunk_type="table",
                        metadata={
                            "source_file": doc.filename,
                            "page": block.page_number,
                            "type": "table",
                            **block.metadata
                        }
                    )
                )
                chunk_counter += 1
                continue

            # RULE 2: Split text blocks using sliding window if exceeding chunk size
            words = block.content.split()
            if len(words) <= self.chunk_size:
                chunk_id = f"{doc.doc_id}_p{block.page_number}_c{chunk_counter}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc.doc_id,
                        content=block.content,
                        page_number=block.page_number,
                        chunk_type="text",
                        metadata={
                            "source_file": doc.filename,
                            "page": block.page_number,
                            "type": "text",
                            **block.metadata
                        }
                    )
                )
                chunk_counter += 1
            else:
                # Sliding window with overlap
                start = 0
                step = max(1, self.chunk_size - self.chunk_overlap)
                while start < len(words):
                    sub_words = words[start : start + self.chunk_size]
                    sub_content = " ".join(sub_words)
                    chunk_id = f"{doc.doc_id}_p{block.page_number}_c{chunk_counter}"

                    chunks.append(
                        Chunk(
                            chunk_id=chunk_id,
                            doc_id=doc.doc_id,
                            content=sub_content,
                            page_number=block.page_number,
                            chunk_type="text",
                            metadata={
                                "source_file": doc.filename,
                                "page": block.page_number,
                                "type": "text",
                                "window_start": start,
                                **block.metadata
                            }
                        )
                    )
                    chunk_counter += 1
                    start += step

        return chunks

