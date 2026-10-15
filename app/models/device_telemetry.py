"""
SQLAlchemy ORM model for device telemetry.

Maps to the ``device_telemetry`` table created in the Supabase migration.
Each row is a single telemetry snapshot sent by an IoT hardware device.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, Index, Integer, String
from sqlalchemy.dialects import postgresql

from app.core.database import Base


class DeviceTelemetry(Base):
    """ORM representation of the ``device_telemetry`` table."""

    __tablename__ = "device_telemetry"

    # BigInteger on Postgres (BIGSERIAL), Integer on SQLite (auto-increments correctly)
    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    device_id = Column(String(255), nullable=False, index=True)
    cpu_utilization = Column(Float, nullable=False)
    memory_usage = Column(Float, nullable=False)
    ping_latency_ms = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        # Composite descending index for per-device historical range queries.
        Index(
            "idx_device_telemetry_device_timestamp",
            "device_id",
            "timestamp",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<DeviceTelemetry(id={self.id}, device_id='{self.device_id}', "
            f"cpu={self.cpu_utilization}, mem={self.memory_usage}, "
            f"ping={self.ping_latency_ms}ms, ts={self.timestamp})>"
        )
