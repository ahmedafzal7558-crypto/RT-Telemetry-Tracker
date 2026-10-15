from app.api.v1.devices import router as devices_router
from app.api.v1.general import router as general_router
from app.api.v1.telemetry import router as telemetry_router

__all__ = ["devices_router", "general_router", "telemetry_router"]
