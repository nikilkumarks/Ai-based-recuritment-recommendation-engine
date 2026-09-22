"""Candidate-only suggested skill paths. Deterministic ontology paths, not ML."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.models import User
from app.models.enums import UserRole
from app.modules.career.schemas import CareerPathListResponse
from app.modules.matching.paths import suggested_growth_neighbors
from app.modules.matching.service import MatchingService


class CareerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.matching = MatchingService(db)

    def list_paths(
        self,
        *,
        user: User,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID | None,
    ) -> CareerPathListResponse:
        if user.role == UserRole.RECRUITER.value:
            raise ForbiddenError("Career paths are private to the candidate.")
        self.matching._require_candidate_access(user, candidate_id)
        context = self.matching._load_context(candidate_id)
        if job_id is None:
            items = suggested_growth_neighbors(
                graph=context.potential_graph,
                index=context.index,
                candidate_skills=context.candidate_skills,
            )
            return CareerPathListResponse(candidate_id=candidate_id, job_id=None, items=items)
        job = self.matching.repo.get_job(job_id)
        if job is None or not self.matching._candidate_may_view_job(user, job):
            raise NotFoundError("Job not found.")
        match = self.matching._score_pair(
            context, job, persist=False, include_career_paths=True
        )
        return CareerPathListResponse(
            candidate_id=candidate_id,
            job_id=job_id,
            items=match.suggested_skill_paths,
        )
