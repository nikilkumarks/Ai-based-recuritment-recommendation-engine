"""Admin-only ontology HTTP routes. Candidates and recruiters cannot mutate the catalog."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.modules.authorization.dependencies import require_admin_role
from app.modules.ontology.schemas import (
    AliasCreate,
    OntologyVersionView,
    RelationCreate,
    SkillCreate,
    SkillListResponse,
    ValidationReport,
    VersionCreate,
)
from app.modules.ontology.service import OntologyService

router = APIRouter(prefix="/admin/ontology", tags=["ontology"])


def get_ontology_service(db: Session = Depends(get_db)) -> OntologyService:
    return OntologyService(db)


@router.get("/skills", response_model=SkillListResponse)
def list_skills(
    _: User = Depends(require_admin_role),
    service: OntologyService = Depends(get_ontology_service),
) -> SkillListResponse:
    return service.list_skills()


@router.post("/skills", response_model=SkillListResponse)
def create_skill(
    payload: SkillCreate,
    user: User = Depends(require_admin_role),
    service: OntologyService = Depends(get_ontology_service),
) -> SkillListResponse:
    service.create_skill(user, payload)
    return service.list_skills()


@router.post("/aliases")
def create_alias(
    payload: AliasCreate,
    user: User = Depends(require_admin_role),
    service: OntologyService = Depends(get_ontology_service),
) -> dict:
    return service.create_alias(user, payload)


@router.post("/relations")
def create_relation(
    payload: RelationCreate,
    user: User = Depends(require_admin_role),
    service: OntologyService = Depends(get_ontology_service),
) -> dict:
    return service.create_relation(user, payload)


@router.get("/versions", response_model=list[OntologyVersionView])
def list_versions(
    _: User = Depends(require_admin_role),
    service: OntologyService = Depends(get_ontology_service),
) -> list[OntologyVersionView]:
    return service.list_versions()


@router.post("/versions", response_model=OntologyVersionView)
def create_version(
    payload: VersionCreate,
    user: User = Depends(require_admin_role),
    service: OntologyService = Depends(get_ontology_service),
) -> OntologyVersionView:
    return service.create_version(user, payload)


@router.get("/validation", response_model=ValidationReport)
def validate_ontology(
    _: User = Depends(require_admin_role),
    service: OntologyService = Depends(get_ontology_service),
) -> ValidationReport:
    return service.validate()


@router.post("/seed", response_model=OntologyVersionView)
def seed(
    _: User = Depends(require_admin_role),
    service: OntologyService = Depends(get_ontology_service),
) -> OntologyVersionView:
    return service.seed()
