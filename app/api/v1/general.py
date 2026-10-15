"""
General endpoints: health check and telemetry retrieval by ID.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.telemetry import HealthResponse, TelemetryRead
from app.services.telemetry_service import delete_telemetry, get_telemetry_by_id

router = APIRouter(tags=["general"])
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
def health() -> HealthResponse:
    """Return basic service metadata."""
    return HealthResponse(
        status="ok", app=settings.APP_NAME, version=settings.APP_VERSION
    )


@router.get(
    "/telemetry/{telemetry_id}",
    response_model=TelemetryRead,
    summary="Retrieve a single telemetry reading by ID",
)
def get_reading(
    telemetry_id: int,
    db: Session = Depends(get_db),
) -> TelemetryRead:
    """Return one telemetry record by its primary key."""
    record = get_telemetry_by_id(db, telemetry_id=telemetry_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Telemetry record {telemetry_id} not found",
        )
    return record


@router.delete(
    "/telemetry/{telemetry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a telemetry reading by ID",
)
def remove_reading(
    telemetry_id: int,
    db: Session = Depends(get_db),
) -> None:
    """Delete one telemetry record by its primary key."""
    deleted: bool = delete_telemetry(db, telemetry_id=telemetry_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Telemetry record {telemetry_id} not found",
        )
