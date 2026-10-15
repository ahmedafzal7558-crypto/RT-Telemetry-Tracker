# IoT Telemetry Processing Engine

A production-ready Python **FastAPI** backend for ingesting, storing, and analyzing telemetry data from IoT hardware devices. The system connects to a **PostgreSQL** relational database via **SQLAlchemy** and includes optimized raw SQL queries for indexed historical device-log lookups.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Directory Structure](#directory-structure)
3. [Database Schema](#database-schema)
4. [Configuration](#configuration)
5. [Docker Setup](#docker-setup)
6. [Running Locally (Without Docker)](#running-locally-without-docker)
7. [API Endpoints](#api-endpoints)
8. [Optimization Service — Raw SQL Details](#optimization-service--raw-sql-details)
9. [Testing](#testing)
10. [Technology Stack](#technology-stack)

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Client / IoT Device                           │
│                   (HTTP POST / GET requests)                         │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐   │
│  │  API Routers │  │  Middleware │  │   Pydantic Schemas          │   │
│  │             │  │   (CORS)    │  │   (Validation & Serialization)│  │
│  └──────┬──────┘  └─────────────┘  └─────────────────────────────┘   │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    Service Layer                              │    │
│  │  ┌────────────────────┐   ┌──────────────────────────────┐   │    │
│  │  │ telemetry_service   │   │ optimization_service         │   │    │
│  │  │ (ORM-based CRUD)    │   │ (Raw SQL indexed queries)    │   │    │
│  │  └─────────┬──────────┘   └──────────────┬───────────────┘   │    │
│  └────────────┼─────────────────────────────┼───────────────────┘    │
└───────────────┼─────────────────────────────┼────────────────────────┘
                │                             │
                ▼                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     SQLAlchemy Core (Engine + Session)               │
│              Connection Pool (pool_size=10, max_overflow=20)         │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    PostgreSQL (Supabase or Self-Hosted)              │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Table: device_telemetry                                       │  │
│  │  Indexes:                                                       │  │
│  │    • idx_device_telemetry_device_id (device_id)                │  │
│  │    • idx_device_telemetry_device_timestamp (device_id, ts DESC)│  │
│  │    • idx_device_telemetry_timestamp (timestamp)                │  │
│  │  RLS: Enabled (anon + authenticated CRUD)                      │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### Design Principles

| Layer | Responsibility | Pattern |
|---|---|---|
| **API Routers** | HTTP request/response handling, input validation | Thin controllers, dependency injection |
| **Service Layer** | Business logic, database operations | ORM + raw SQL hybrid |
| **Models** | ORM table mapping | SQLAlchemy declarative |
| **Schemas** | Request/response validation & serialization | Pydantic v2 |
| **Core** | Configuration, database engine/session | Singleton settings, factory sessions |

The architecture follows a **layered separation of concerns**: routers never touch the database directly, services never construct HTTP responses, and schemas are the single source of truth for data shapes at API boundaries.

---

## Directory Structure

```
iot-telemetry-engine/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app instance, middleware, router wiring
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                    # Pydantic-settings configuration
│   │   └── database.py                  # SQLAlchemy engine, session factory, get_db dependency
│   ├── models/
│   │   ├── __init__.py
│   │   └── device_telemetry.py          # SQLAlchemy ORM model
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── telemetry.py                 # Pydantic request/response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── telemetry_service.py         # CRUD operations (ORM-based)
│   │   └── optimization_service.py      # Raw SQL indexed lookup queries
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── general.py               # Health check, get-by-id, delete
│           ├── telemetry.py             # Ingest (single + batch), list
│           └── devices.py               # Device analytics + optimization endpoints
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Pytest fixtures (in-memory SQLite)
│   ├── test_telemetry.py                # Ingestion & listing tests
│   └── test_devices.py                  # Device analytics tests
├── .env.example                         # Environment variable template
├── .gitignore
├── Dockerfile                           # Production container image
├── docker-compose.yml                   # Container orchestration
├── requirements.txt                     # Python dependencies
└── README.md
```

---

## Database Schema

### Table: `device_telemetry`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `BIGSERIAL` | Primary Key | Auto-incrementing row ID |
| `device_id` | `TEXT` | NOT NULL | Unique hardware device identifier |
| `cpu_utilization` | `DOUBLE PRECISION` | NOT NULL | CPU usage percentage (0.0–100.0) |
| `memory_usage` | `DOUBLE PRECISION` | NOT NULL | Memory usage percentage (0.0–100.0) |
| `ping_latency_ms` | `INTEGER` | NOT NULL | Network ping latency in milliseconds |
| `timestamp` | `TIMESTAMPTZ` | NOT NULL | UTC timestamp of the reading |

### Indexes

| Index Name | Columns | Purpose |
|---|---|---|
| `idx_device_telemetry_device_id` | `device_id` | Fast per-device lookups |
| `idx_device_telemetry_device_timestamp` | `device_id, timestamp DESC` | Composite index for historical range queries per device |
| `idx_device_telemetry_timestamp` | `timestamp` | Cross-device time-range queries |

### Row Level Security

RLS is enabled with permissive `anon, authenticated` policies for all CRUD operations, as this is a single-tenant IoT ingestion backend without a sign-in screen.

---

## Configuration

All settings are loaded from environment variables (or a `.env` file) via `pydantic-settings`.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/iot_telemetry` | SQLAlchemy connection string |
| `DEBUG` | `False` | Enable SQLAlchemy echo logging |
| `APP_NAME` | `IoT Telemetry Processing Engine` | Application name |
| `APP_VERSION` | `1.0.0` | Application version |
| `API_PREFIX` | `/api/v1` | URL prefix for all API routes |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

---

## Docker Setup

### Prerequisites

- Docker Engine 24+
- Docker Compose v2+

### Steps

1. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd iot-telemetry-engine
   ```

2. **Create a `.env` file:**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `DATABASE_URL` to your PostgreSQL connection string:

   ```env
   DATABASE_URL=postgresql://user:password@host:5432/dbname
   ```

3. **Build and start the container:**

   ```bash
   docker compose up --build -d
   ```

4. **Verify the service is running:**

   ```bash
   curl http://localhost:8000/api/v1/health
   ```

   Expected response:

   ```json
   {"status": "ok", "app": "IoT Telemetry Processing Engine", "version": "1.0.0"}
   ```

5. **Access the interactive API docs:**

   Open `http://localhost:8000/docs` in your browser for the Swagger UI, or `http://localhost:8000/redoc` for ReDoc.

6. **Stop the container:**

   ```bash
   docker compose down
   ```

---

## Running Locally (Without Docker)

### Prerequisites

- Python 3.12+
- PostgreSQL 14+ (or a Supabase project)

### Steps

1. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   # venv\Scripts\activate    # Windows
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the database:**

   ```bash
   cp .env.example .env
   # Edit .env with your DATABASE_URL
   ```

4. **Start the development server:**

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the API:**

   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`
   - Health check: `http://localhost:8000/api/v1/health`

---

## API Endpoints

All endpoints are prefixed with `/api/v1`.

### Health & General

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Root info — returns app metadata and docs URL |
| `GET` | `/health` | Service health check |
| `GET` | `/telemetry/{id}` | Retrieve a single telemetry reading by ID |
| `DELETE` | `/telemetry/{id}` | Delete a telemetry reading by ID |

### Telemetry Ingestion

| Method | Path | Description |
|---|---|---|
| `POST` | `/telemetry` | Ingest a single telemetry reading |
| `POST` | `/telemetry/batch` | Ingest up to 5,000 readings in one request |
| `GET` | `/telemetry` | List readings (paginated, filterable by device and time range) |

### Device Analytics & Optimization

| Method | Path | Description |
|---|---|---|
| `GET` | `/devices/{device_id}/history` | Historical readings for a device (indexed range scan) |
| `GET` | `/devices/{device_id}/latest` | Most recent reading for a device |
| `GET` | `/devices/{device_id}/count` | Count readings in a time window (index-only scan) |
| `GET` | `/devices/{device_id}/summary` | Aggregated CPU/memory/ping statistics |
| `GET` | `/devices/{device_id}/buckets` | 1-minute bucketed averages |
| `GET` | `/devices/high-cpu` | Devices exceeding a CPU threshold in a time window |
| `GET` | `/devices/{device_id}/explain` | EXPLAIN plan for the historical range query |

### Example Requests

**Ingest a single reading:**

```bash
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "raspberry-pi-01",
    "cpu_utilization": 72.5,
    "memory_usage": 58.3,
    "ping_latency_ms": 24,
    "timestamp": "2026-01-15T10:30:00Z"
  }'
```

**Ingest a batch:**

```bash
curl -X POST http://localhost:8000/api/v1/telemetry/batch \
  -H "Content-Type: application/json" \
  -d '[
    {
      "device_id": "raspberry-pi-01",
      "cpu_utilization": 72.5,
      "memory_usage": 58.3,
      "ping_latency_ms": 24,
      "timestamp": "2026-01-15T10:30:00Z"
    },
    {
      "device_id": "raspberry-pi-02",
      "cpu_utilization": 91.0,
      "memory_usage": 82.1,
      "ping_latency_ms": 150,
      "timestamp": "2026-01-15T10:31:00Z"
    }
  ]'
```

**List readings with filters:**

```bash
curl "http://localhost:8000/api/v1/telemetry?device_id=raspberry-pi-01&page=1&page_size=20"
```

**Get historical range for a device:**

```bash
curl "http://localhost:8000/api/v1/devices/raspberry-pi-01/history?start_time=2026-01-15T00:00:00Z&end_time=2026-01-16T00:00:00Z&limit=100"
```

**Get latest reading:**

```bash
curl http://localhost:8000/api/v1/devices/raspberry-pi-01/latest
```

**Get device summary:**

```bash
curl http://localhost:8000/api/v1/devices/raspberry-pi-01/summary
```

**Find high-CPU devices:**

```bash
curl "http://localhost:8000/api/v1/devices/high-cpu?start_time=2026-01-15T00:00:00Z&end_time=2026-01-16T00:00:00Z&threshold=90.0"
```

**Get bucketed averages:**

```bash
curl "http://localhost:8000/api/v1/devices/raspberry-pi-01/buckets?start_time=2026-01-15T00:00:00Z&end_time=2026-01-16T00:00:00Z"
```

**View EXPLAIN plan:**

```bash
curl "http://localhost:8000/api/v1/devices/raspberry-pi-01/explain?start_time=2026-01-15T00:00:00Z&end_time=2026-01-16T00:00:00Z"
```

---

## Optimization Service — Raw SQL Details

The `optimization_service.py` module contains six raw SQL query strings executed through SQLAlchemy's `text()` construct. Each query is designed to use one or more of the table's indexes to avoid sequential scans on large telemetry tables.

### Query 1: Historical Range Lookup

```sql
SELECT id, device_id, cpu_utilization, memory_usage, ping_latency_ms, timestamp
FROM   device_telemetry
WHERE  device_id = :device_id
  AND  timestamp >= :start_time
  AND  timestamp <= :end_time
ORDER BY timestamp DESC
LIMIT  :limit
```

**Index used:** `idx_device_telemetry_device_timestamp` (composite on `device_id, timestamp DESC`)

The composite index allows the query planner to seek directly to the device's partition of the index and scan only the relevant timestamp range in descending order, then apply the LIMIT — all without touching the heap for rows outside the range.

### Query 2: Latest Reading

```sql
SELECT id, device_id, cpu_utilization, memory_usage, ping_latency_ms, timestamp
FROM   device_telemetry
WHERE  device_id = :device_id
ORDER BY timestamp DESC
LIMIT 1
```

**Index used:** `idx_device_telemetry_device_timestamp`

The descending ordering in the composite index means the planner can fetch the top row for a device via a simple index seek — no sort step required.

### Query 3: Count in Range

```sql
SELECT COUNT(*) AS reading_count
FROM   device_telemetry
WHERE  device_id = :device_id
  AND  timestamp >= :start_time
  AND  timestamp <= :end_time
```

**Index used:** `idx_device_telemetry_device_timestamp`

For count queries, PostgreSQL can perform an index-only scan (when the visibility map is up to date), counting matching index entries without visiting the heap.

### Query 4: High-CPU Devices

```sql
SELECT DISTINCT device_id
FROM   device_telemetry
WHERE  timestamp >= :start_time
  AND  timestamp <= :end_time
  AND  cpu_utilization >= :threshold
ORDER BY device_id
```

**Index used:** `idx_device_telemetry_timestamp` for the time range, then a filter on `cpu_utilization`.

### Query 5: Bucketed Averages

```sql
SELECT date_trunc('minute', timestamp) AS bucket,
       AVG(cpu_utilization) AS avg_cpu,
       AVG(memory_usage)    AS avg_mem,
       AVG(ping_latency_ms) AS avg_ping,
       COUNT(*)             AS sample_count
FROM   device_telemetry
WHERE  device_id = :device_id
  AND  timestamp >= :start_time
  AND  timestamp <= :end_time
GROUP BY bucket
ORDER BY bucket ASC
```

**Index used:** `idx_device_telemetry_device_timestamp` for the range scan; grouping operates on the same indexed column.

### Query 6: EXPLAIN Plan

```sql
EXPLAIN (FORMAT TEXT)
SELECT id, device_id, cpu_utilization, memory_usage, ping_latency_ms, timestamp
FROM   device_telemetry
WHERE  device_id = :device_id
  AND  timestamp >= :start_time
  AND  timestamp <= :end_time
ORDER BY timestamp DESC
LIMIT  :limit
```

This is exposed via the `/devices/{device_id}/explain` endpoint so you can verify at runtime that the planner is using an **Index Scan** or **Index Only Scan** on the composite index, rather than falling back to a **Seq Scan**.

---

## Testing

Tests use an in-memory SQLite database and FastAPI's `TestClient` — no Postgres required.

```bash
# Install dev dependencies (already in requirements.txt)
pip install -r requirements.txt

# Run all tests
pytest -v

# Run with coverage
pytest -v --tb=short
```

### Test Files

| File | Coverage |
|---|---|
| `tests/test_telemetry.py` | Health check, single ingest, batch ingest, listing, get-by-id, delete, 404 cases |
| `tests/test_devices.py` | Latest reading, summary, historical range, count in range, 404 cases |

---

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Web framework | FastAPI | 0.115.6 |
| ASGI server | Uvicorn | 0.34.0 |
| ORM | SQLAlchemy | 2.0.36 |
| Validation | Pydantic | 2.10.4 |
| Settings | pydantic-settings | 2.7.0 |
| Database | PostgreSQL | 14+ |
| Database driver | psycopg2-binary | 2.9.10 |
| Testing | pytest + httpx | 8.3.4 / 0.28.1 |
| Containerization | Docker + Docker Compose | — |

---

## License

This project is provided as-is for educational and production use.
