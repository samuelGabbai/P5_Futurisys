FROM ghcr.io/astral-sh/uv:0.10.9 AS uv
FROM python:3.13-slim

COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --extra api --no-dev --no-install-project
COPY api.py audit.py database.py inference.py schemas.py ./
COPY artifacts/turnover_model.joblib ./artifacts/turnover_model.joblib
COPY examples/predict.json ./examples/predict.json
COPY scripts/check_deployment.py ./scripts/check_deployment.py
RUN useradd --uid 10001 --create-home hrnova
USER hrnova
ENV PATH="/app/.venv/bin:$PATH" HRNOVA_MODEL_PATH=/app/artifacts/turnover_model.joblib
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
