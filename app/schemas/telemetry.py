"""
Pydantic schemas for telemetry request/response validation and serialization.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TelemetryBase(BaseModel):
    """Shared fields for create and read operations."""

    device_id: str = Field(..., min_length=1, max_length=255, description="Hardware device identifier")
    cpu_utilization: float = Field(..., ge=0.0, le=100.0, description="CPU usage percentage (0–100)")
    memory_usage: float = Field(..., ge=0.0, le=100.0, description="Memory usage percentage (0–100)")
    ping_latency_ms: int = Field(..., ge=0, description="Network ping latency in milliseconds")
    timestamp: datetime = Field(..., description="UTC timestamp of the reading")


class TelemetryCreate(TelemetryBase):
    """Schema for accepting a single telemetry reading."""
    pass


class TelemetryBatchCreate(BaseModel):
    """Schema for accepting a batch of telemetry readings in one request."""

    readings: List[TelemetryCreate] = Field(
        ..., min_length=1, max_length=5000, description="List of telemetry readings"
    )


class TelemetryRead(TelemetryBase):
    """Schema for returning a telemetry reading with its database ID."""

    id: int

    model_config = {"from_attributes": True}


class TelemetryBatchResponse(BaseModel):
    """Response after a batch ingest."""

    inserted: int = Field(..., description="Number of readings stored")
    device_ids: List[str] = Field(..., description="Distinct device IDs in the batch")


class TelemetryListResponse(BaseModel):
    """Paginated list of telemetry readings."""

    total: int
    page: int
    page_size: int
    items: List[TelemetryRead]


class DeviceSummary(BaseModel):
    """Aggregated statistics for a single device."""

    device_id: str
    reading_count: int
    avg_cpu_utilization: float
    avg_memory_usage: float
    avg_ping_latency_ms: float
    max_cpu_utilization: float
    max_memory_usage: float
    max_ping_latency_ms: int
    min_cpu_utilization: float
    min_memory_usage: float
    min_ping_latency_ms: int
    first_reading: datetime
    last_reading: datetime


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str
    app: str
    version: str
