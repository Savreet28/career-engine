# ---------------------------------------------------------------------------
# Career Engine — single-container deployment (Hugging Face Spaces)
# ---------------------------------------------------------------------------
# Stage 1 builds the React frontend; stage 2 runs FastAPI and serves that
# build from the same origin, so the browser never makes a cross-origin call.
#
# The sentence-transformer model is downloaded at BUILD time, not at first
# request, so the first visitor does not wait ~20s for a 90 MB download.
# ---------------------------------------------------------------------------

# ---- stage 1: build the frontend ------------------------------------------
FROM node:22-slim AS frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


# ---- stage 2: backend + built frontend ------------------------------------
FROM python:3.12-slim

# Hugging Face Spaces runs the container as uid 1000, which cannot write to /.
# Everything that needs to be written at runtime lives under /home/user.
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /home/user/app

# Install dependencies first so this layer is cached across code changes.
# The CPU-only torch wheel is ~200 MB instead of the ~2.5 GB CUDA build.
COPY --chown=user backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

COPY --chown=user backend/ ./backend/
COPY --chown=user --from=frontend /build/dist ./frontend/dist

USER user

# Warm the model cache at build time.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

ENV FRONTEND_DIST=/home/user/app/frontend/dist \
    PORT=7860
EXPOSE 7860

WORKDIR /home/user/app/backend
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
