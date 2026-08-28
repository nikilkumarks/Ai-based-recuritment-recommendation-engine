from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    service: str


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Infrastructure liveness probe. Does not report ML or ranking status."""
    return HealthResponse(status="ok", service="api")
