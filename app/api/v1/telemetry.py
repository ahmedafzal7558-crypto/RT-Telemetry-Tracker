"""
Telemetry ingestion and listing endpoints.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.telemetry import (
    TelemetryBatchResponse,
    TelemetryCreate,
    TelemetryListResponse,
    TelemetryRead,
)
from app.services.telemetry_service import (
    create_telemetry,
    create_telemetry_batch,
    list_telemetry,
)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])
settings = get_settings()


@router.post(
    "",
    response_model=TelemetryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single telemetry reading",
)
def ingest_single(
    payload: TelemetryCreate,
    db: Session = Depends(get_db),
) -> TelemetryRead:
    """Accept and store a single device telemetry reading."""
    return create_telemetry(db, payload)


@router.post(
    "/batch",
    response_model=TelemetryBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a batch of telemetry readings",
)
def ingest_batch(
    readings: list[TelemetryCreate],
    db: Session = Depends(get_db),
) -> TelemetryBatchResponse:
    """Accept and store up to 5,000 telemetry readings in one request."""
    return create_telemetry_batch(db, readings)


@router.get(
    "",
    response_model=TelemetryListResponse,
    summary="List telemetry readings (paginated, filterable)",
)
def list_readings(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(
        50, ge=1, le=1000, description="Items per page"
    ),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
    start_time: Optional[datetime] = Query(None, description="ISO-8601 lower bound (inclusive)"),
    end_time: Optional[datetime] = Query(None, description="ISO-8601 upper bound (inclusive)"),
) -> TelemetryListResponse:
    """Return a paginated list of telemetry readings, optionally filtered."""
    total, items = list_telemetry(
        db,
        page=page,
        page_size=page_size,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
    )
    return TelemetryListResponse(
        total=total, page=page, page_size=page_size, items=items
    )
