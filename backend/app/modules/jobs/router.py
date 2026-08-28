"""HTTP routes for jobs and extracted requirements. Organization-scoped."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import User
from app.modules.identity.dependencies import get_current_active_user
from app.modules.jobs.schemas import (
    JobCreate,
    JobDetail,
    JobListResponse,
    JobRequirementUpdate,
    JobRequirementView,
)
from app.modules.jobs.service import JobService

router = APIRouter(tags=["jobs"])


def get_job_service(db: Session = Depends(get_db)) -> JobService:
    return JobService(db)


@router.post("/jobs", response_model=JobDetail, status_code=201)
def create_job(
    payload: JobCreate,
    user: User = Depends(get_current_active_user),
    service: JobService = Depends(get_job_service),
) -> JobDetail:
    return service.create_job(user=user, payload=payload)


@router.get("/jobs", response_model=JobListResponse)
def list_jobs(
    user: User = Depends(get_current_active_user),
    service: JobService = Depends(get_job_service),
) -> JobListResponse:
    return service.list_jobs(user=user)


@router.get("/jobs/{job_id}", response_model=JobDetail)
def get_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: JobService = Depends(get_job_service),
) -> JobDetail:
    return service.get_job(user=user, job_id=job_id)


@router.post("/jobs/{job_id}/extract", response_model=JobRequirementView)
def extract_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: JobService = Depends(get_job_service),
) -> JobRequirementView:
    return service.extract(user=user, job_id=job_id)


@router.put("/jobs/{job_id}/requirements", response_model=JobRequirementView)
def update_requirements(
    job_id: uuid.UUID,
    payload: JobRequirementUpdate,
    user: User = Depends(get_current_active_user),
    service: JobService = Depends(get_job_service),
) -> JobRequirementView:
    return service.update_requirements(user=user, job_id=job_id, payload=payload)


@router.post("/jobs/{job_id}/requirements/confirm", response_model=JobRequirementView)
def confirm_requirements(
    job_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    service: JobService = Depends(get_job_service),
) -> JobRequirementView:
    return service.confirm(user=user, job_id=job_id)
