"""
Service layer for telemetry CRUD operations.

All functions accept a SQLAlchemy ``Session`` so callers (typically FastAPI
dependencies) control the transaction lifecycle.
"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.device_telemetry import DeviceTelemetry
from app.schemas.telemetry import (
    DeviceSummary,
    TelemetryBatchResponse,
    TelemetryCreate,
    TelemetryRead,
)


def create_telemetry(db: Session, data: TelemetryCreate) -> TelemetryRead:
    """Persist a single telemetry reading and return the stored record."""
    record = DeviceTelemetry(
        device_id=data.device_id,
        cpu_utilization=data.cpu_utilization,
        memory_usage=data.memory_usage,
        ping_latency_ms=data.ping_latency_ms,
        timestamp=data.timestamp,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return TelemetryRead.model_validate(record)


def create_telemetry_batch(
    db: Session, readings: List[TelemetryCreate]
) -> TelemetryBatchResponse:
    """Persist a batch of telemetry readings in a single transaction."""
    records: List[DeviceTelemetry] = []
    for reading in readings:
        records.append(
            DeviceTelemetry(
                device_id=reading.device_id,
                cpu_utilization=reading.cpu_utilization,
                memory_usage=reading.memory_usage,
                ping_latency_ms=reading.ping_latency_ms,
                timestamp=reading.timestamp,
            )
        )
    db.add_all(records)
    db.commit()

    device_ids: List[str] = list({r.device_id for r in readings})
    return TelemetryBatchResponse(inserted=len(records), device_ids=device_ids)


def list_telemetry(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    device_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Tuple[int, List[TelemetryRead]]:
    """Return a paginated, optionally filtered list of telemetry readings."""
    query = select(DeviceTelemetry)

    if device_id is not None:
        query = query.where(DeviceTelemetry.device_id == device_id)
    if start_time is not None:
        query = query.where(DeviceTelemetry.timestamp >= start_time)
    if end_time is not None:
        query = query.where(DeviceTelemetry.timestamp <= end_time)

    # Total count for pagination metadata
    count_query = select(func.count()).select_from(query.subquery())
    total: int = db.execute(count_query).scalar_one()

    # Order by timestamp descending (most recent first)
    query = query.order_by(DeviceTelemetry.timestamp.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    rows: List[DeviceTelemetry] = list(db.execute(query).scalars().all())
    items: List[TelemetryRead] = [TelemetryRead.model_validate(r) for r in rows]
    return total, items


def get_telemetry_by_id(db: Session, telemetry_id: int) -> Optional[TelemetryRead]:
    """Return a single telemetry record by primary key, or None."""
    record: Optional[DeviceTelemetry] = db.get(DeviceTelemetry, telemetry_id)
    if record is None:
        return None
    return TelemetryRead.model_validate(record)


def delete_telemetry(db: Session, telemetry_id: int) -> bool:
    """Delete a telemetry record by ID. Returns True if a row was deleted."""
    record: Optional[DeviceTelemetry] = db.get(DeviceTelemetry, telemetry_id)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True


def get_device_summary(db: Session, device_id: str) -> Optional[DeviceSummary]:
    """Aggregate statistics for a specific device across all its readings."""
    query = select(
        func.count(DeviceTelemetry.id).label("reading_count"),
        func.avg(DeviceTelemetry.cpu_utilization).label("avg_cpu"),
        func.avg(DeviceTelemetry.memory_usage).label("avg_mem"),
        func.avg(DeviceTelemetry.ping_latency_ms).label("avg_ping"),
        func.max(DeviceTelemetry.cpu_utilization).label("max_cpu"),
        func.max(DeviceTelemetry.memory_usage).label("max_mem"),
        func.max(DeviceTelemetry.ping_latency_ms).label("max_ping"),
        func.min(DeviceTelemetry.cpu_utilization).label("min_cpu"),
        func.min(DeviceTelemetry.memory_usage).label("min_mem"),
        func.min(DeviceTelemetry.ping_latency_ms).label("min_ping"),
        func.min(DeviceTelemetry.timestamp).label("first_reading"),
        func.max(DeviceTelemetry.timestamp).label("last_reading"),
    ).where(DeviceTelemetry.device_id == device_id)

    row = db.execute(query).one()
    if row.reading_count == 0:
        return None

    return DeviceSummary(
        device_id=device_id,
        reading_count=int(row.reading_count),
        avg_cpu_utilization=round(float(row.avg_cpu), 4),
        avg_memory_usage=round(float(row.avg_mem), 4),
        avg_ping_latency_ms=round(float(row.avg_ping), 2),
        max_cpu_utilization=float(row.max_cpu),
        max_memory_usage=float(row.max_mem),
        max_ping_latency_ms=int(row.max_ping),
        min_cpu_utilization=float(row.min_cpu),
        min_memory_usage=float(row.min_mem),
        min_ping_latency_ms=int(row.min_ping),
        first_reading=row.first_reading,
        last_reading=row.last_reading,
    )
