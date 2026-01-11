# ---------- Builder ----------
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- Runtime ----------
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app
COPY --from=builder /usr/local /usr/local

COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic
COPY app /app/app

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# NOTE:
# - Migrations are executed on container start to reduce manual steps for evaluation.
# - In production, migrations are typically handled via CI/CD or controlled rollout procedures.
CMD ["bash", "-lc", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
