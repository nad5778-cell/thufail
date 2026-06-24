# Thufail — PIC Data Validation & Analytics Portal

Internal web app for validating and analyzing insurance-company (PIC) data sourced
from a read-only Oracle database view/synonym layer.

## Stack

- **Backend:** Python (FastAPI) + `python-oracledb` (read-only)
- **Frontend:** React (Vite)

## Structure

```
backend/   FastAPI service: config, DB access, PIC summary/detail APIs
frontend/  React dashboard: PIC summary cards/charts + drill-down record explorer
```

## Backend setup

```
cd backend
cp .env.example .env   # fill in Oracle connection + view names
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend only ever queries the views/synonyms listed in `.env`
(`ORACLE_PIC_SUMMARY_VIEW`, `ORACLE_PIC_DETAIL_VIEW`). It never issues DDL/DML and
uses a read-only Oracle session.

## Frontend setup

```
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` in `frontend/.env` to point at the backend (default
`http://localhost:8000`).

## Anomaly detection

`GET /api/pic/{pic_code}/anomalies/national-identity` runs rule checks
(empty/format/duplicate) plus a PyTorch autoencoder pattern-anomaly score over
NATIONAL_IDENTITY for one PIC, sourced from the read-only view configured as
`ORACLE_MEMBER_VIEW` (must expose `NATIONAL_IDENTITY`, `FIRST_NAME`,
`INSURANCE_COMPANY_NUMBER`). `.../national-identity.xlsx` downloads the same
result as a styled Excel dashboard.

## Deploying internally (Docker)

```
cp backend/.env.example backend/.env   # fill in real Oracle connection + view names
VITE_API_BASE_URL=http://<your-server-hostname>:8000 docker compose up -d --build
```

- `VITE_API_BASE_URL` is baked into the frontend at build time and must be an
  address reachable from users' browsers (not the Docker network), e.g. your
  internal server's hostname/IP or a reverse-proxy URL.
- Frontend serves on port 80, backend API on port 8000 — adjust the published
  ports in `docker-compose.yml` if those clash with anything else on the host.
- Re-run `docker compose up -d --build` to pick up code or `.env` changes.

No Kubernetes/ingress config is included; if your internal platform needs it,
say so and it can be added.

## Status

Read/view-only dashboard with PIC summary metrics, drill-down to underlying
records, and a NATIONAL_IDENTITY anomaly check. Additional validation rules
(other fields, reconciliation against external sources) can be added once
defined.
