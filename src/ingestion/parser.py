"""Layout-aware document parser.

Extracts text blocks and table structures from enterprise documents (PDF, Markdown, TXT),
preserving table geometry as Markdown tables so retrieval models retain tabular semantics.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import re


@dataclass
class ContentBlock:
    """Represents a discrete semantic block (paragraph or table) in a document."""
    content: str
    block_type: str  # "text", "table", "header"
    page_number: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Represents a fully ingested and parsed document."""
    doc_id: str
    filename: str
    file_path: str
    blocks: List[ContentBlock]
    total_pages: int
    raw_text: str


class DocumentParser:
    """Extracts text and structured tables from various document formats."""

    def __init__(self):
        pass

    def parse(self, file_path: str | Path) -> ParsedDocument:
        """Parses a document file and returns a structured ParsedDocument."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document not found at {path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(path)
        elif suffix in [".txt", ".md", ".markdown"]:
            return self._parse_text(path)
        else:
            raise ValueError(f"Unsupported document format: {suffix}. Supported: .pdf, .txt, .md")

    def _parse_pdf(self, path: Path) -> ParsedDocument:
        """Extracts text and tables from PDF files using pdfplumber if available, falling back to pypdf."""
        blocks: List[ContentBlock] = []
        raw_text_parts: List[str] = []
        doc_id = path.stem.lower().replace(" ", "_")

        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                total_pages = len(pdf.pages)
                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1

                    # 1. Extract structured tables first
                    tables = page.extract_tables() or []
                    for t_idx, table in enumerate(tables):
                        table_md = self._table_to_markdown(table)
                        if table_md.strip():
                            blocks.append(
                                ContentBlock(
                                    content=table_md,
                                    block_type="table",
                                    page_number=page_num,
                                    metadata={"table_index": t_idx, "doc_id": doc_id}
                                )
                            )
                            raw_text_parts.append(table_md)

                    # 2. Extract regular text
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        # Split by major paragraphs
                        paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
                        for p in paragraphs:
                            blocks.append(
                                ContentBlock(
                                    content=p,
                                    block_type="text",
                                    page_number=page_num,
                                    metadata={"doc_id": doc_id}
                                )
                            )
                        raw_text_parts.append(page_text)

        except ImportError:
            # Fallback to PyPDF
            import pypdf
            reader = pypdf.PdfReader(str(path))
            total_pages = len(reader.pages)
            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                text = page.extract_text() or ""
                if text.strip():
                    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
                    for p in paragraphs:
                        blocks.append(
                            ContentBlock(
                                content=p,
                                block_type="text",
                                page_number=page_num,
                                metadata={"doc_id": doc_id}
                            )
                        )
                    raw_text_parts.append(text)

        return ParsedDocument(
            doc_id=doc_id,
            filename=path.name,
            file_path=str(path.resolve()),
            blocks=blocks,
            total_pages=total_pages if 'total_pages' in locals() else 1,
            raw_text="\n\n".join(raw_text_parts)
        )

    def _parse_text(self, path: Path) -> ParsedDocument:
        """Parses raw text or markdown files preserving table section context."""
        content = path.read_text(encoding="utf-8")
        doc_id = path.stem.lower().replace(" ", "_")
        blocks: List[ContentBlock] = []

        paragraphs = re.split(r"\n{2,}", content)
        current_section = ""

        for idx, para in enumerate(paragraphs):
            p = para.strip()
            if not p:
                continue

            if p.startswith("#"):
                current_section = p.lstrip("#").strip()

            is_table = ("|" in p and ("---" in p or "-|-" in p)) or (p.startswith("|") and p.count("|") >= 4)
            if is_table:
                # Ensure clean markdown linebreaks across all rows
                table_lines = [line.strip() for line in p.splitlines() if line.strip()]
                clean_table = "\n".join(table_lines)

                # If preceding block was an introductory caption (e.g. mentions 'table' or ends with ':'),
                # merge it into the table block so it does not become an orphan snippet.
                caption = ""
                if blocks and (
                    len(blocks[-1].content) < 160
                    or "table" in blocks[-1].content.lower()
                    or blocks[-1].content.strip().endswith(":")
                ):
                    last_block = blocks.pop()
                    caption = last_block.content

                table_parts = []
                if current_section and current_section not in clean_table:
                    table_parts.append(f"### {current_section}")
                if caption:
                    table_parts.append(caption)
                table_parts.append(clean_table)

                full_table_content = "\n\n".join(table_parts)

                blocks.append(
                    ContentBlock(
                        content=full_table_content,
                        block_type="table",
                        page_number=1,
                        metadata={"doc_id": doc_id, "block_index": idx, "section": current_section}
                    )
                )
            else:
                blocks.append(
                    ContentBlock(
                        content=p,
                        block_type="text",
                        page_number=1,
                        metadata={"doc_id": doc_id, "block_index": idx, "section": current_section}
                    )
                )

        return ParsedDocument(
            doc_id=doc_id,
            filename=path.name,
            file_path=str(path.resolve()),
            blocks=blocks,
            total_pages=1,
            raw_text=content
        )

    @staticmethod
    def _table_to_markdown(table: List[List[Optional[str]]]) -> str:
        """Converts raw 2D grid from PDF tables into clean Markdown table format."""
        if not table or len(table) < 2:
            return ""

        clean_table = []
        for row in table:
            clean_row = [str(cell or "").replace("\n", " ").strip() for cell in row]
            if any(clean_row):
                clean_table.append(clean_row)

        if not clean_table:
            return ""

        headers = clean_table[0]
        separator = ["---"] * len(headers)
        rows = clean_table[1:]

        md_lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(separator) + " |"
        ]
        for row in rows:
            # Pad row if missing columns
            padded = row + [""] * (len(headers) - len(row))
            md_lines.append("| " + " | ".join(padded[:len(headers)]) + " |")

        return "\n".join(md_lines)

