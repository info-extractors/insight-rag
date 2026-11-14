FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=7860

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up user for Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Install Python requirements
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY --chown=user:user src/ ./src/
COPY --chown=user:user data/ ./data/
COPY --chown=user:user tests/ ./tests/
COPY --chown=user:user app.py .
COPY --chown=user:user .env.example .env

# Create cache and index directories with proper permissions
RUN mkdir -p /app/data/index /home/user/.cache && chown -R user:user /app /home/user

USER user

# Hugging Face Spaces standard port
EXPOSE 7860

CMD ["streamlit", "run", "src/app/ui.py", "--server.port", "7860", "--server.address", "0.0.0.0"]
