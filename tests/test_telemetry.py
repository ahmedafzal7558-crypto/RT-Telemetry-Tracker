"""
Tests for the telemetry ingestion and listing endpoints.
"""

from datetime import datetime, timezone


def test_health(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "version" in data


def test_ingest_single(client) -> None:
    payload = {
        "device_id": "device-001",
        "cpu_utilization": 45.5,
        "memory_usage": 60.2,
        "ping_latency_ms": 12,
        "timestamp": datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc).isoformat(),
    }
    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["device_id"] == "device-001"
    assert data["cpu_utilization"] == 45.5
    assert data["memory_usage"] == 60.2
    assert data["ping_latency_ms"] == 12
    assert "id" in data


def test_ingest_batch(client) -> None:
    readings = [
        {
            "device_id": "device-001",
            "cpu_utilization": 30.0,
            "memory_usage": 50.0,
            "ping_latency_ms": 5,
            "timestamp": datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc).isoformat(),
        },
        {
            "device_id": "device-002",
            "cpu_utilization": 90.0,
            "memory_usage": 85.0,
            "ping_latency_ms": 200,
            "timestamp": datetime(2026, 1, 15, 10, 5, 0, tzinfo=timezone.utc).isoformat(),
        },
    ]
    response = client.post("/api/v1/telemetry/batch", json=readings)
    assert response.status_code == 201
    data = response.json()
    assert data["inserted"] == 2
    assert set(data["device_ids"]) == {"device-001", "device-002"}


def test_list_telemetry(client) -> None:
    # Ingest a reading first
    payload = {
        "device_id": "device-001",
        "cpu_utilization": 45.5,
        "memory_usage": 60.2,
        "ping_latency_ms": 12,
        "timestamp": datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc).isoformat(),
    }
    client.post("/api/v1/telemetry", json=payload)

    response = client.get("/api/v1/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1


def test_get_telemetry_by_id(client) -> None:
    payload = {
        "device_id": "device-001",
        "cpu_utilization": 45.5,
        "memory_usage": 60.2,
        "ping_latency_ms": 12,
        "timestamp": datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc).isoformat(),
    }
    create_response = client.post("/api/v1/telemetry", json=payload)
    telemetry_id: int = create_response.json()["id"]

    response = client.get(f"/api/v1/telemetry/{telemetry_id}")
    assert response.status_code == 200
    assert response.json()["id"] == telemetry_id


def test_get_telemetry_not_found(client) -> None:
    response = client.get("/api/v1/telemetry/99999")
    assert response.status_code == 404


def test_delete_telemetry(client) -> None:
    payload = {
        "device_id": "device-001",
        "cpu_utilization": 45.5,
        "memory_usage": 60.2,
        "ping_latency_ms": 12,
        "timestamp": datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc).isoformat(),
    }
    create_response = client.post("/api/v1/telemetry", json=payload)
    telemetry_id: int = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/telemetry/{telemetry_id}")
    assert delete_response.status_code == 204

    # Verify it's gone
    get_response = client.get(f"/api/v1/telemetry/{telemetry_id}")
    assert get_response.status_code == 404
