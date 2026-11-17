
FROM node:20-slim AS frontend-builder
WORKDIR /build


COPY frontend/package*.json ./
RUN npm install

# Copy source and compile to /build/dist
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Python Backend Runtime
# ==========================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Install minimal OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and app directory with full ownership
RUN useradd -m -u 1000 user && \
    mkdir -p /app/data/chroma_db /app/data/user_documents /app/data/models && \
    chown -R user:user /app

USER user
ENV HOME=/home/user \
    PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Install Python dependencies
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy backend code
COPY --chown=user:user app/ ./app/

# Copy precompiled frontend assets from Stage 1
COPY --chown=user:user --from=frontend-builder /build/dist ./frontend/dist

# Cloud Run injects $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "python -m uvicorn app.api.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
