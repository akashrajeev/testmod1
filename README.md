# Ledgerly

A production-oriented full-stack personal expense tracker built with React + TypeScript, FastAPI, PostgreSQL, JWT authentication, and Docker Compose.

## Architecture

- `backend/`: FastAPI API, SQLAlchemy 2 ORM, Alembic migrations, Pydantic schemas, JWT auth, CSV import/export, pytest suite.
- `frontend/`: React + TypeScript + Vite single-page app with TanStack Query and React Router.
- `docker-compose.yml`: PostgreSQL, backend, and frontend services.

### Important decisions

- **SQLAlchemy 2 + Alembic:** explicit relational models and repeatable database migrations.
- **Argon2 password hashing:** memory-hard password hashing with `argon2-cffi`.
- **JWT access tokens:** stateless API authentication. The frontend keeps the short-lived token in `sessionStorage` and sends it as a Bearer token.
- **Money as integer cents:** avoids floating-point currency errors in the database and API.
- **Server-side filtering/pagination:** keeps list and dashboard queries scalable.
- **CSV streaming:** import/export operates row-by-row rather than loading entire files into memory.
- **Ownership enforcement:** expense queries are always scoped to the authenticated user's ID.

## Project structure

```text
.
├── backend
│   ├── app
│   │   ├── api
│   │   ├── core
│   │   ├── db
│   │   ├── schemas
│   │   ├── services
│   │   └── main.py
│   ├── alembic
│   ├── tests
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── alembic.ini
├── frontend
│   ├── src
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── vite.config.ts
├── .env.example
├── docker-compose.yml
└── README.md
```

## Local setup

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
cp ../.env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

## Docker setup

```bash
cp .env.example .env
docker compose up --build
```

Then open `http://localhost:5173`.

The backend is available at `http://localhost:8000`, with OpenAPI docs at `http://localhost:8000/docs`.

## Environment variables

See `.env.example` for all supported variables. Never commit real secrets.

- `DATABASE_URL`
- `JWT_SECRET`
- `JWT_EXPIRES_MINUTES`
- `CORS_ORIGINS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`

## Database migrations

Create a migration after model changes:

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Tests

```bash
cd backend
pytest
```

The test suite uses an isolated in-memory SQLite database for fast behavioral tests while the production configuration uses PostgreSQL.

## API overview

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/expenses`
- `POST /api/expenses`
- `GET /api/expenses/{id}`
- `PATCH /api/expenses/{id}`
- `DELETE /api/expenses/{id}`
- `GET /api/expenses/export/csv`
- `POST /api/expenses/import`
- `GET /api/dashboard/summary`

## Security notes

Passwords are never stored in plaintext. All expense endpoints require a valid JWT and apply user ownership predicates at the query boundary. CORS is explicitly configured rather than wildcarded by default.

## Known limitations

- Access tokens are intentionally short-lived and there is no refresh-token rotation flow yet.
- Logout is client-side token invalidation; already-issued tokens remain valid until expiration.
- CSV duplicate detection is based on an import-row fingerprint within the target user account.
