from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for InsightRAG using Pydantic Settings."""

    APP_NAME: str = "InsightRAG"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000

    # Project Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    SAMPLE_DOCS_DIR: Path = DATA_DIR / "sample_docs"
    INDEX_DIR: Path = DATA_DIR / "index"
    CHROMA_PERSIST_DIR: Path = INDEX_DIR / "chroma"

    # Embedding and Reranker Models
    DENSE_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Hybrid Retrieval Constants
    TOP_K_RETRIEVAL: int = 10
    TOP_K_RERANKED: int = 3
    RRF_K_CONSTANT: int = 60

    # Chunking Hyperparameters
    CHUNK_SIZE: int = 400  # Words / token approximation
    CHUNK_OVERLAP: int = 80

    # LLM Provider Configuration (Choices: "qwen", "mock", "gemini", "openai")
    LLM_PROVIDER: Literal["qwen", "mock", "gemini", "openai"] = "qwen"
    QWEN_MODEL_NAME: str = "Qwen/Qwen2.5-0.5B-Instruct"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
settings.INDEX_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

