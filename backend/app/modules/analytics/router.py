"""Analytics and admin dataset HTTP. Descriptive only; does not train models."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.modules.analytics.schemas import (
    AdminUserListResponse,
    DatasetSnapshotDetail,
    DatasetSnapshotSummary,
    FunnelAnalytics,
    MlModelSummary,
    RecruiterMatchingAnalytics,
    RecruiterOverview,
    RecruiterSkillsAnalytics,
)
from app.modules.analytics.service import AnalyticsService
from app.modules.identity.dependencies import get_current_active_user

router = APIRouter(tags=["analytics"])


def get_analytics_service(db: Session = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/analytics/recruiter/overview", response_model=RecruiterOverview)
def recruiter_overview(
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> RecruiterOverview:
    return service.recruiter_overview(user)


@router.get("/analytics/recruiter/skills", response_model=RecruiterSkillsAnalytics)
def recruiter_skills(
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> RecruiterSkillsAnalytics:
    return service.recruiter_skills(user)


@router.get("/analytics/recruiter/matching", response_model=RecruiterMatchingAnalytics)
def recruiter_matching(
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> RecruiterMatchingAnalytics:
    return service.recruiter_matching(user)


@router.get("/analytics/recruiter/funnel", response_model=FunnelAnalytics)
def recruiter_funnel(
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> FunnelAnalytics:
    return service.recruiter_funnel(user)


@router.get("/analytics/admin/overview", response_model=RecruiterOverview)
def admin_overview(
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> RecruiterOverview:
    return service.admin_overview(user)


@router.get("/analytics/admin/skills", response_model=RecruiterSkillsAnalytics)
def admin_skills(
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> RecruiterSkillsAnalytics:
    return service.admin_skills(user)


@router.get("/admin/users", response_model=AdminUserListResponse)
def list_admin_users(
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AdminUserListResponse:
    return service.list_users(user)


@router.get("/analytics/candidates/{candidate_id}/overview", response_model=RecruiterMatchingAnalytics)
def candidate_overview(
    candidate_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> RecruiterMatchingAnalytics:
    return service.candidate_overview(user, candidate_id)


@router.post("/admin/datasets/snapshots", response_model=DatasetSnapshotDetail, status_code=201)
def create_dataset_snapshot(
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> DatasetSnapshotDetail:
    """Create a point-in-time dataset snapshot. Does not train a model."""
    return service.create_dataset(user)


@router.get("/admin/datasets/snapshots", response_model=list[DatasetSnapshotSummary])
def list_dataset_snapshots(
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[DatasetSnapshotSummary]:
    return service.list_datasets(user)


@router.get("/admin/datasets/snapshots/{snapshot_id}", response_model=DatasetSnapshotDetail)
def get_dataset_snapshot(
    snapshot_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> DatasetSnapshotDetail:
    return service.get_dataset(user, snapshot_id)


@router.get("/admin/models", response_model=list[MlModelSummary])
def list_models(
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[MlModelSummary]:
    return service.list_models(user)


@router.get("/admin/models/{model_id}", response_model=MlModelSummary)
def get_model(
    model_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> MlModelSummary:
    return service.get_model(user, model_id)


@router.post("/admin/models/{model_id}/activate", response_model=MlModelSummary)
def activate_model(
    model_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> MlModelSummary:
    return service.activate_model(user, model_id)


@router.post("/admin/models/{model_id}/reject", response_model=MlModelSummary)
def reject_model(
    model_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> MlModelSummary:
    return service.reject_model(user, model_id)
