from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, http_exception_handler, validation_exception_handler
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    get_settings().assert_secure_for_environment()
    from app.modules.nlp.pipeline import warm_nlp

    warm_nlp()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="PRJ_385 API",
        version="0.7.0",
        description=(
            "AI-Based Recruitment Recommendation Engine. "
            "Phase 7: interpretable baseline matching. "
            "Baseline scores are not trained ML and not accuracy. "
            "No ranking or ML training endpoints."
        ),
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.include_router(api_v1_router, prefix="/api/v1")
    return application


app = create_app()
