# Realtime Monitoring System (FastAPI + WebSocket + Streamlit + MariaDB)

This repository contains:
- FastAPI RESTful APIs + WebSocket realtime push
- JWT authentication + RBAC (Admin/User/Viewer)
- MariaDB 11.7 persistence using SQLAlchemy ORM (asyncmy) + Alembic migrations
- Streamlit multi-page UI
- Docker + Docker Compose deployment

## Quick Start (Docker Compose)

1) Create `.env` from `.env.example` and keep it out of version control.

```bash
cp .env.example .env
```

2) Start

```bash
docker compose up --build
```

3) Access

Streamlit UI: http://localhost:8501

FastAPI Swagger: http://localhost:8000/docs

# Test Accounts (seeded, demo only)
Password: Password123! (change for production)

admin@example.com (ADMIN)

user@example.com (USER)

viewer@example.com (VIEWER)
