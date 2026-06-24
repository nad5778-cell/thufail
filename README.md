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

## Status

This is the first iteration: a read/view-only dashboard with PIC summary
metrics and drill-down to underlying records. Validation rules (business-rule
checks, reconciliation) are intentionally not yet implemented and will be
added as a follow-up once the specific rules are defined.
