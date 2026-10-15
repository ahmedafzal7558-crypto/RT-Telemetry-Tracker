"""
Tests for the device analytics and optimization endpoints.
"""

from datetime import datetime, timezone


def _seed_readings(client, device_id: str, count: int = 3) -> None:
    """Helper: ingest ``count`` readings for a device."""
    readings = []
    for i in range(count):
        readings.append(
            {
                "device_id": device_id,
                "cpu_utilization": 50.0 + i * 10,
                "memory_usage": 40.0 + i * 5,
                "ping_latency_ms": 10 + i * 5,
                "timestamp": datetime(
                    2026, 1, 15, 10 + i, 0, 0, tzinfo=timezone.utc
                ).isoformat(),
            }
        )
    client.post("/api/v1/telemetry/batch", json=readings)


def test_get_latest_reading(client) -> None:
    _seed_readings(client, "device-001", 3)
    response = client.get("/api/v1/devices/device-001/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "device-001"
    assert data["cpu_utilization"] == 70.0


def test_get_latest_not_found(client) -> None:
    response = client.get("/api/v1/devices/unknown/latest")
    assert response.status_code == 404


def test_get_summary(client) -> None:
    _seed_readings(client, "device-001", 3)
    response = client.get("/api/v1/devices/device-001/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "device-001"
    assert data["reading_count"] == 3
    assert data["max_cpu_utilization"] == 70.0
    assert data["min_cpu_utilization"] == 50.0


def test_get_summary_not_found(client) -> None:
    response = client.get("/api/v1/devices/unknown/summary")
    assert response.status_code == 404


def test_history_range(client) -> None:
    _seed_readings(client, "device-001", 3)
    start = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    response = client.get(
        f"/api/v1/devices/device-001/history?start_time={start}&end_time={end}"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    # Should be ordered by timestamp DESC
    assert data[0]["cpu_utilization"] == 70.0


def test_count_in_range(client) -> None:
    _seed_readings(client, "device-001", 3)
    start = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    end = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    response = client.get(
        f"/api/v1/devices/device-001/count?start_time={start}&end_time={end}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["reading_count"] == 3
