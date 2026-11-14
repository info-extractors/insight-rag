"""Unit tests for DocumentParser and DocumentChunker."""

import pytest
from pathlib import Path
from src.ingestion.parser import DocumentParser, ParsedDocument
from src.ingestion.chunker import DocumentChunker


def test_markdown_parsing_and_table_extraction(tmp_path: Path):
    sample_content = (
        "# Quarterly Statement\n\n"
        "Revenue increased significantly this quarter.\n\n"
        "| Quarter | Revenue ($M) | Profit ($M) |\n"
        "|---|---|---|\n"
        "| Q1 | 120 | 25 |\n"
        "| Q2 | 145 | 32 |\n\n"
        "Outlook remains highly optimistic for Q3."
    )
    test_file = tmp_path / "report.md"
    test_file.write_text(sample_content, encoding="utf-8")

    parser = DocumentParser()
    parsed_doc = parser.parse(test_file)

    assert parsed_doc.doc_id == "report"
    assert len(parsed_doc.blocks) == 3
    # Check that table block is extracted cleanly
    table_blocks = [b for b in parsed_doc.blocks if b.block_type == "table"]
    assert len(table_blocks) == 1
    assert "Revenue ($M)" in table_blocks[0].content


def test_chunking_preserves_tables(tmp_path: Path):
    sample_content = (
        "Introduction paragraph about corporate governance.\n\n"
        "| Metric | Target | Actual |\n"
        "|---|---|---|\n"
        "| Operating Margin | 25% | 27.5% |\n"
    )
    test_file = tmp_path / "gov.md"
    test_file.write_text(sample_content, encoding="utf-8")

    parser = DocumentParser()
    doc = parser.parse(test_file)

    chunker = DocumentChunker(chunk_size=10, chunk_overlap=2)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 2
    table_chunks = [c for c in chunks if c.chunk_type == "table"]
    assert len(table_chunks) == 1
    assert "Operating Margin" in table_chunks[0].content

