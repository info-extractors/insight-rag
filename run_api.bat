@echo off
echo Starting InsightRAG FastAPI REST Backend...
python -m uvicorn src.app.api:app --host 0.0.0.0 --port 8000 --reload
pause

