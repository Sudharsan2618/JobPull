FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
EXPOSE 8080

# Cloud Run service default: the FastAPI app (the API the Next.js UI consumes).
# Shell form so Cloud Run's $PORT is expanded. Cloud Run Jobs override this CMD
# with `--command=python --args=pipeline.py`.
CMD exec uvicorn app.server:app --host 0.0.0.0 --port ${PORT:-8080}
