"""
Optimization service for indexed historical device-log lookups.

This module demonstrates the use of **raw SQL query strings** executed through
SQLAlchemy's ``text()`` construct. Each query is crafted to leverage the
indexes defined on the ``device_telemetry`` table:

  - ``idx_device_telemetry_device_id``  — B-tree on ``device_id``
  - ``idx_device_telemetry_device_timestamp`` — composite on ``(device_id, timestamp DESC)``
  - ``idx_device_telemetry_timestamp``  — B-tree on ``timestamp``

By filtering on ``device_id`` and a timestamp range, the planner can use the
composite index to satisfy the query with an index-only scan, avoiding full
sequential scans on large telemetry tables.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


# ──────────────────────────────────────────────────────────────────────────────
# Raw SQL query strings
# ──────────────────────────────────────────────────────────────────────────────

# Query 1 — Historical range lookup for a specific device.
# Uses idx_device_telemetry_device_timestamp for an indexed range scan.
SQL_HISTORICAL_RANGE = text("""
    SELECT  id,
            device_id,
            cpu_utilization,
            memory_usage,
            ping_latency_ms,
            timestamp
    FROM    device_telemetry
    WHERE   device_id = :device_id
      AND   timestamp >= :start_time
      AND   timestamp <= :end_time
    ORDER BY timestamp DESC
    LIMIT   :limit
""")

# Query 2 — Latest reading for a device.
# The composite index (device_id, timestamp DESC) lets the planner pick the
# top row via an index scan without sorting.
SQL_LATEST_READING = text("""
    SELECT  id,
            device_id,
            cpu_utilization,
            memory_usage,
            ping_latency_ms,
            timestamp
    FROM    device_telemetry
    WHERE   device_id = :device_id
    ORDER BY timestamp DESC
    LIMIT 1
""")

# Query 3 — Count of readings in a time window for a device.
# Uses idx_device_telemetry_device_timestamp for a count via index range scan.
SQL_COUNT_IN_RANGE = text("""
    SELECT  COUNT(*) AS reading_count
    FROM    device_telemetry
    WHERE   device_id = :device_id
      AND   timestamp >= :start_time
      AND   timestamp <= :end_time
""")

# Query 4 — Devices with high CPU utilization above a threshold in a time window.
# Uses idx_device_telemetry_timestamp for the time range, then filters by CPU.
SQL_HIGH_CPU_DEVICES = text("""
    SELECT  DISTINCT device_id
    FROM    device_telemetry
    WHERE   timestamp >= :start_time
      AND   timestamp <= :end_time
      AND   cpu_utilization >= :threshold
    ORDER BY device_id
""")

# Query 5 — Time-bucketed averages (1-minute buckets) for a device.
# Leverages the composite index for the range scan; the bucketing is done
# with date_trunc on the indexed timestamp column.
SQL_BUCKETED_AVERAGES = text("""
    SELECT  date_trunc('minute', timestamp) AS bucket,
            AVG(cpu_utilization)            AS avg_cpu,
            AVG(memory_usage)               AS avg_mem,
            AVG(ping_latency_ms)            AS avg_ping,
            COUNT(*)                        AS sample_count
    FROM    device_telemetry
    WHERE   device_id = :device_id
      AND   timestamp >= :start_time
      AND   timestamp <= :end_time
    GROUP BY bucket
    ORDER BY bucket ASC
""")

# Query 6 — Explain plan for the historical range query (for debugging).
SQL_EXPLAIN_RANGE = text("""
    EXPLAIN (FORMAT TEXT)
    SELECT  id, device_id, cpu_utilization, memory_usage, ping_latency_ms, timestamp
    FROM    device_telemetry
    WHERE   device_id = :device_id
      AND   timestamp >= :start_time
      AND   timestamp <= :end_time
    ORDER BY timestamp DESC
    LIMIT   :limit
""")


# ──────────────────────────────────────────────────────────────────────────────
# Service functions
# ──────────────────────────────────────────────────────────────────────────────

def _row_to_dict(row: Any) -> Dict[str, Any]:
    """Convert a SQLAlchemy Row to a plain dict."""
    return dict(row._mapping)


def get_historical_range(
    db: Session,
    device_id: str,
    start_time: datetime,
    end_time: datetime,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """
    Retrieve historical telemetry readings for a device within a time range.

    Executes a raw SQL query that uses the composite index
    ``idx_device_telemetry_device_timestamp`` for an efficient indexed range
    scan instead of a full table scan.
    """
    result = db.execute(
        SQL_HISTORICAL_RANGE,
        {
            "device_id": device_id,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        },
    )
    return [_row_to_dict(row) for row in result.fetchall()]


def get_latest_reading(
    db: Session, device_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve the most recent telemetry reading for a device.

    Uses the composite index ``(device_id, timestamp DESC)`` so the planner
    can fetch the top row directly without a sort step.
    """
    result = db.execute(SQL_LATEST_READING, {"device_id": device_id})
    row = result.fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def count_readings_in_range(
    db: Session,
    device_id: str,
    start_time: datetime,
    end_time: datetime,
) -> int:
    """
    Count telemetry readings for a device in a time window.

    Uses ``idx_device_telemetry_device_timestamp`` for an index-only count.
    """
    result = db.execute(
        SQL_COUNT_IN_RANGE,
        {
            "device_id": device_id,
            "start_time": start_time,
            "end_time": end_time,
        },
    )
    return int(result.scalar_one())


def find_high_cpu_devices(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    threshold: float = 90.0,
) -> List[str]:
    """
    Find all device IDs that reported CPU utilization above a threshold
    within the given time window.

    Uses ``idx_device_telemetry_timestamp`` for the time-range filter.
    """
    result = db.execute(
        SQL_HIGH_CPU_DEVICES,
        {
            "start_time": start_time,
            "end_time": end_time,
            "threshold": threshold,
        },
    )
    return [str(row[0]) for row in result.fetchall()]


def get_bucketed_averages(
    db: Session,
    device_id: str,
    start_time: datetime,
    end_time: datetime,
) -> List[Dict[str, Any]]:
    """
    Return 1-minute-bucketed averages of CPU, memory, and ping for a device.

    The range scan uses ``idx_device_telemetry_device_timestamp``; the
    grouping is done on ``date_trunc('minute', timestamp)`` which operates
    on the same indexed column.
    """
    result = db.execute(
        SQL_BUCKETED_AVERAGES,
        {
            "device_id": device_id,
            "start_time": start_time,
            "end_time": end_time,
        },
    )
    rows: List[Dict[str, Any]] = []
    for row in result.fetchall():
        mapping = _row_to_dict(row)
        rows.append(
            {
                "bucket": mapping["bucket"],
                "avg_cpu_utilization": round(float(mapping["avg_cpu"]), 4)
                if mapping["avg_cpu"] is not None
                else None,
                "avg_memory_usage": round(float(mapping["avg_mem"]), 4)
                if mapping["avg_mem"] is not None
                else None,
                "avg_ping_latency_ms": round(float(mapping["avg_ping"]), 2)
                if mapping["avg_ping"] is not None
                else None,
                "sample_count": int(mapping["sample_count"]),
            }
        )
    return rows


def explain_range_query(
    db: Session,
    device_id: str,
    start_time: datetime,
    end_time: datetime,
    limit: int = 1000,
) -> List[str]:
    """
    Run ``EXPLAIN`` on the historical range query and return the plan lines.

    Useful for verifying that the planner uses the composite index rather
    than falling back to a sequential scan.
    """
    result = db.execute(
        SQL_EXPLAIN_RANGE,
        {
            "device_id": device_id,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        },
    )
    return [str(row[0]) for row in result.fetchall()]
