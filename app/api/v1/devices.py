"""
Device analytics and optimization endpoints.

These endpoints demonstrate the raw-SQL optimization queries from
``optimization_service`` — indexed historical lookups, latest-reading
fetches, high-CPU detection, and time-bucketed aggregations.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.telemetry import DeviceSummary
from app.services.optimization_service import (
    count_readings_in_range,
    explain_range_query,
    find_high_cpu_devices,
    get_bucketed_averages,
    get_historical_range,
    get_latest_reading,
)
from app.services.telemetry_service import get_device_summary, get_telemetry_by_id

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get(
    "/{device_id}/history",
    summary="Historical telemetry for a device (indexed range lookup)",
)
def get_history(
    device_id: str,
    db: Session = Depends(get_db),
    start_time: datetime = Query(..., description="ISO-8601 lower bound (inclusive)"),
    end_time: datetime = Query(..., description="ISO-8601 upper bound (inclusive)"),
    limit: int = Query(1000, ge=1, le=10000, description="Max rows to return"),
) -> list[dict]:
    """
    Retrieve historical readings for a device within a time range using a
    raw SQL query that leverages the composite index
    ``(device_id, timestamp DESC)`` for an efficient indexed range scan.
    """
    return get_historical_range(
        db, device_id=device_id, start_time=start_time, end_time=end_time, limit=limit
    )


@router.get(
    "/{device_id}/latest",
    summary="Latest telemetry reading for a device",
)
def get_latest(
    device_id: str,
    db: Session = Depends(get_db),
) -> Optional[dict]:
    """
    Return the most recent reading for a device, fetched via an indexed
    lookup on ``(device_id, timestamp DESC)``.
    """
    reading: Optional[dict] = get_latest_reading(db, device_id=device_id)
    if reading is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No telemetry found for device '{device_id}'",
        )
    return reading


@router.get(
    "/{device_id}/count",
    summary="Count readings in a time window (index-only scan)",
)
def get_count(
    device_id: str,
    db: Session = Depends(get_db),
    start_time: datetime = Query(..., description="ISO-8601 lower bound (inclusive)"),
    end_time: datetime = Query(..., description="ISO-8601 upper bound (inclusive)"),
) -> dict:
    """Return the number of readings a device logged in the given window."""
    count: int = count_readings_in_range(
        db, device_id=device_id, start_time=start_time, end_time=end_time
    )
    return {"device_id": device_id, "reading_count": count}


@router.get(
    "/{device_id}/summary",
    response_model=DeviceSummary,
    summary="Aggregated statistics for a device",
)
def get_summary(
    device_id: str,
    db: Session = Depends(get_db),
) -> DeviceSummary:
    """Return aggregated CPU, memory, and latency stats for a device."""
    summary: Optional[DeviceSummary] = get_device_summary(db, device_id=device_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No telemetry found for device '{device_id}'",
        )
    return summary


@router.get(
    "/{device_id}/buckets",
    summary="1-minute bucketed averages for a device",
)
def get_buckets(
    device_id: str,
    db: Session = Depends(get_db),
    start_time: datetime = Query(..., description="ISO-8601 lower bound (inclusive)"),
    end_time: datetime = Query(..., description="ISO-8601 upper bound (inclusive)"),
) -> list[dict]:
    """
    Return per-minute averages of CPU, memory, and ping latency for a device,
    computed via a raw SQL ``date_trunc`` grouping on the indexed timestamp.
    """
    return get_bucketed_averages(
        db, device_id=device_id, start_time=start_time, end_time=end_time
    )


@router.get(
    "/high-cpu",
    summary="Devices with CPU utilization above a threshold",
)
def high_cpu(
    db: Session = Depends(get_db),
    start_time: datetime = Query(..., description="ISO-8601 lower bound (inclusive)"),
    end_time: datetime = Query(..., description="ISO-8601 upper bound (inclusive)"),
    threshold: float = Query(90.0, ge=0.0, le=100.0, description="CPU % threshold"),
) -> dict:
    """Return device IDs that exceeded a CPU utilization threshold in a time window."""
    devices: List[str] = find_high_cpu_devices(
        db, start_time=start_time, end_time=end_time, threshold=threshold
    )
    return {"threshold": threshold, "device_ids": devices, "count": len(devices)}


@router.get(
    "/{device_id}/explain",
    summary="EXPLAIN plan for the historical range query",
)
def get_explain(
    device_id: str,
    db: Session = Depends(get_db),
    start_time: datetime = Query(..., description="ISO-8601 lower bound (inclusive)"),
    end_time: datetime = Query(..., description="ISO-8601 upper bound (inclusive)"),
    limit: int = Query(1000, ge=1, le=10000),
) -> dict:
    """
    Run ``EXPLAIN`` on the historical range query and return the plan lines.
    Use this to verify the planner uses the composite index rather than a
    sequential scan.
    """
    plan: List[str] = explain_range_query(
        db, device_id=device_id, start_time=start_time, end_time=end_time, limit=limit
    )
    return {"device_id": device_id, "plan": plan}
