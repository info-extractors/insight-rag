"""FastAPI REST Service for InsightRAG."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.app.pipeline import InsightRAGPipeline
from src.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Multimodal RAG & Query-to-Insight Platform with Hybrid Search & Guardrails",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline instance
pipeline = InsightRAGPipeline()


# --- Pydantic Schemas ---
class QueryRequest(BaseModel):
    query: str = Field(..., example="What was the total cloud revenue in FY2024 and what was the growth rate?")
    top_k_candidates: Optional[int] = Field(default=10, ge=1, le=50)
    top_k_final: Optional[int] = Field(default=3, ge=1, le=10)


class CitationSchema(BaseModel):
    doc_id: str
    page_number: int
    source_file: str
    snippet: str


class GuardrailSchema(BaseModel):
    passed: bool
    faithfulness_score: float
    verified_citations: int
    unverified_citations: int
    hallucinated_numbers: List[str]
    warnings: List[str]


class EvaluationSchema(BaseModel):
    context_relevance: float
    groundedness: float
    answer_relevance: float
    composite_rag_score: float
    details: Dict[str, Any]


class QueryResponseSchema(BaseModel):
    query: str
    answer: str
    citations: List[CitationSchema]
    retrieved_chunks: List[Dict[str, Any]]
    guardrail: GuardrailSchema
    evaluation: EvaluationSchema
    latency_breakdown_ms: Dict[str, float]
    total_latency_ms: float


class IngestResponseSchema(BaseModel):
    status: str
    doc_id: str
    filename: str
    total_pages: int
    blocks_extracted: int
    chunks_indexed: int
    ingestion_time_ms: float


# --- API Routes ---
@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """Returns application health and operational status."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV
    }


@app.get("/api/v1/stats", tags=["System"])
async def system_stats():
    """Returns database size, indexed documents, and model settings."""
    return pipeline.stats()


@app.post("/api/v1/ingest", response_model=IngestResponseSchema, tags=["Ingestion"])
async def ingest_document(file: UploadFile = File(...)):
    """Uploads and indexes an enterprise document (PDF, TXT, MD)."""
    allowed_exts = [".pdf", ".txt", ".md", ".markdown"]
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(allowed_exts)}"
        )

    # Save to local sample_docs directory
    save_path = settings.SAMPLE_DOCS_DIR / file.filename
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        result = pipeline.ingest_file(save_path)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document: {str(e)}"
        )


@app.post("/api/v1/query", response_model=QueryResponseSchema, tags=["Retrieval & Reasoning"])
async def query_insights(request: QueryRequest):
    """Executes end-to-end hybrid retrieval, reranking, generation, and guardrail auditing."""
    if pipeline.dense_store.count() == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents have been indexed yet. Please ingest a document first."
        )

    try:
        response = pipeline.query(
            text=request.query,
            top_k_candidates=request.top_k_candidates or settings.TOP_K_RETRIEVAL,
            top_k_final=request.top_k_final or settings.TOP_K_RERANKED
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing query: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.app.api:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)

