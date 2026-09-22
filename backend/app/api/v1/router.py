from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.modules.analytics.router import router as analytics_router
from app.modules.applications.router import router as applications_router
from app.modules.authorization.router import router as authz_router
from app.modules.candidates.router import router as candidates_router
from app.modules.career.router import router as career_router
from app.modules.documents.router import router as documents_router
from app.modules.embeddings.router import router as embeddings_router
from app.modules.identity.router import router as auth_router
from app.modules.jobs.router import router as jobs_router
from app.modules.matching.router import router as matching_router
from app.modules.ontology.router import router as ontology_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(authz_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(candidates_router)
api_v1_router.include_router(jobs_router)
api_v1_router.include_router(ontology_router)
api_v1_router.include_router(embeddings_router)
api_v1_router.include_router(matching_router)
api_v1_router.include_router(career_router)
api_v1_router.include_router(applications_router)
api_v1_router.include_router(analytics_router)
