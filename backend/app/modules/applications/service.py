"""Append-only recruiter decisions. Not hiring outcomes and not model training."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, UnprocessableError
from app.models import Application, CandidateDecision, RecruiterDecision, User
from app.models.enums import ApplicationStatus, CandidateDecisionAction, UserRole
from app.modules.applications.constants import (
    PRODUCT_ACTIONS,
    REASON_CODES,
    RECRUITER_HIRED,
    RECRUITER_REJECTED,
    RECRUITER_REVIEWED,
    RECRUITER_SHORTLISTED,
)
from app.modules.applications.repository import ApplicationsRepository
from app.modules.applications.schemas import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationView,
    CandidateDecisionCreate,
    CandidateDecisionView,
    RecruiterDecisionCreate,
    RecruiterDecisionListResponse,
    RecruiterDecisionView,
)
from app.modules.authorization.service import AuthorizationService
from app.modules.identity import audit
from app.modules.identity.tokens import utcnow
from app.modules.nlp.repository import NlpRepository



class ApplicationsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ApplicationsRepository(db)
        self.authz = AuthorizationService(db)

    def create_decision(
        self,
        *,
        user: User,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
        payload: RecruiterDecisionCreate,
    ) -> RecruiterDecisionView:
        if user.role != UserRole.RECRUITER.value:
            raise ForbiddenError("Only recruiters can create recruiter decisions.")
        job = self.authz.require_job_org_access(user, job_id)
        self.authz.require_recruiter_candidate_scope(user, candidate_id)
        if payload.action not in PRODUCT_ACTIONS:
            raise UnprocessableError("Unsupported recruiter decision.")
        if payload.reason is not None and payload.reason not in REASON_CODES:
            raise UnprocessableError("Unsupported recruiter reason.")
        now = datetime.now(timezone.utc)
        snapshot = self.repo.snapshot_at_or_before(
            candidate_id=candidate_id, job_id=job.id, when=now
        )
        row = RecruiterDecision(
            recruiter_id=user.id,
            organization_id=job.organization_id,
            job_id=job.id,
            candidate_id=candidate_id,
            action=payload.action,
            reason=payload.reason,
            note=payload.note,
            match_run_id=snapshot.match_run_id if snapshot is not None else None,
            feature_snapshot_id=snapshot.id if snapshot is not None else None,
            decision_metadata={},
            created_at=now,
        )
        self.repo.add_decision(row)

        # Update candidate application status if application exists
        app_row = self.repo.get_application(candidate_id, job.id)
        if app_row is not None:
            if payload.action == "hire":
                app_row.status = ApplicationStatus.SELECTED.value
            elif payload.action == "shortlist":
                app_row.status = ApplicationStatus.SHORTLISTED.value
            elif payload.action == "reject":
                app_row.status = ApplicationStatus.REJECTED.value
            elif payload.action == "review":
                app_row.status = ApplicationStatus.UNDER_REVIEW.value
            self.db.flush()

        audit.record_audit(
            self.db,
            action=_audit_action(payload.action),
            resource_type="recruiter_decision",
            actor_user_id=user.id,
            resource_id=row.id,
            metadata={
                "job_id": str(job.id),
                "candidate_id": str(candidate_id),
                "action": payload.action,
                "reason": payload.reason,
                "match_run_id": str(row.match_run_id) if row.match_run_id else None,
                "feature_snapshot_id": str(row.feature_snapshot_id)
                if row.feature_snapshot_id
                else None,
            },
        )
        self.db.flush()
        return _to_view(row, include_note=True)

    def list_decisions(
        self,
        *,
        user: User,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> RecruiterDecisionListResponse:
        if user.role == UserRole.CANDIDATE.value:
            raise ForbiddenError("Candidates cannot view recruiter decision history.")
        if user.role == UserRole.ADMIN.value:
            job = self.repo.get_job(job_id)
            if job is None:
                raise NotFoundError("Job not found.")
        else:
            job = self.authz.require_job_org_access(user, job_id)
            self.authz.require_recruiter_candidate_scope(user, candidate_id)
        include_note = user.role in {UserRole.RECRUITER.value, UserRole.ADMIN.value}
        items = [
            _to_view(row, include_note=include_note)
            for row in self.repo.list_decisions(job.id, candidate_id)
        ]
        current = items[-1].action if items else None
        return RecruiterDecisionListResponse(
            job_id=job.id,
            candidate_id=candidate_id,
            current_action=current,
            items=items,
        )

    def create_application(
        self, *, user: User, candidate_id: uuid.UUID, job_id: uuid.UUID
    ) -> ApplicationView:
        self.authz.require_candidate_owner(user, candidate_id)
        job = self.repo.get_job(job_id)
        if job is None or job.status in {"closed", "archived"}:
            raise NotFoundError("Job is not available for applications.")
        nlp_repo = NlpRepository(self.db)
        if nlp_repo.latest_confirmed_profile(candidate_id) is None:
            raise ConflictError("Confirm your profile before applying to a job.")
        existing = self.repo.get_application(candidate_id, job.id)
        if existing is not None:
            raise ConflictError("You have already applied to this job.")
        row = Application(
            candidate_id=candidate_id,
            job_id=job.id,
            status=ApplicationStatus.APPLIED.value,
            applied_at=utcnow(),
        )
        self.repo.add_application(row)
        # Also record candidate decision
        self.repo.add_candidate_decision(
            CandidateDecision(
                candidate_id=candidate_id,
                job_id=job.id,
                action=CandidateDecisionAction.APPLY.value,
                created_at=utcnow(),
            )
        )
        audit.record_audit(
            self.db,
            action="candidate_applied",
            resource_type="application",
            actor_user_id=user.id,
            resource_id=row.id,
            metadata={"job_id": str(job.id)},
        )
        self.db.flush()
        return ApplicationView(
            id=row.id,
            candidate_id=row.candidate_id,
            job_id=job.id,
            job_title=job.title,
            job_status=job.status,
            status=row.status,
            applied_at=row.applied_at,
        )

    def list_candidate_applications(
        self, *, user: User, candidate_id: uuid.UUID
    ) -> ApplicationListResponse:
        self.authz.require_candidate_owner(user, candidate_id)
        apps = self.repo.list_candidate_applications(candidate_id)
        return ApplicationListResponse(
            items=[
                ApplicationView(
                    id=row.id,
                    candidate_id=row.candidate_id,
                    job_id=row.job_id,
                    job_title=row.job.title if row.job else "Job",
                    job_status=row.job.status if row.job else "open",
                    status=row.status,
                    applied_at=row.applied_at,
                )
                for row in apps
            ]
        )

    def get_candidate_application(
        self, *, user: User, candidate_id: uuid.UUID, job_id: uuid.UUID
    ) -> ApplicationView | None:
        self.authz.require_candidate_owner(user, candidate_id)
        row = self.repo.get_application(candidate_id, job_id)
        if row is None:
            return None
        job = self.repo.get_job(job_id)
        return ApplicationView(
            id=row.id,
            candidate_id=row.candidate_id,
            job_id=row.job_id,
            job_title=job.title if job else "Job",
            job_status=job.status if job else "open",
            status=row.status,
            applied_at=row.applied_at,
        )

    def create_candidate_decision(
        self, *, user: User, candidate_id: uuid.UUID, job_id: uuid.UUID, action: str
    ) -> CandidateDecisionView:
        self.authz.require_candidate_owner(user, candidate_id)
        job = self.repo.get_job(job_id)
        if job is None:
            raise NotFoundError("Job not found.")
        row = CandidateDecision(
            candidate_id=candidate_id,
            job_id=job.id,
            action=action,
            created_at=utcnow(),
        )
        self.repo.add_candidate_decision(row)
        self.db.flush()
        return CandidateDecisionView(
            id=row.id,
            candidate_id=row.candidate_id,
            job_id=row.job_id,
            action=row.action,
            created_at=row.created_at,
        )

    def list_saved_jobs(self, *, user: User, candidate_id: uuid.UUID) -> list[uuid.UUID]:
        self.authz.require_candidate_owner(user, candidate_id)
        return [job.id for job in self.repo.list_saved_jobs(candidate_id)]


def _to_view(row: RecruiterDecision, *, include_note: bool) -> RecruiterDecisionView:
    return RecruiterDecisionView(
        id=row.id,
        recruiter_id=row.recruiter_id,
        organization_id=row.organization_id,
        job_id=row.job_id,
        candidate_id=row.candidate_id,
        action=row.action,
        reason=row.reason,
        note=row.note if include_note else None,
        match_run_id=row.match_run_id,
        feature_snapshot_id=row.feature_snapshot_id,
        created_at=row.created_at,
    )


def _audit_action(action: str) -> str:
    mapping = {
        "shortlist": RECRUITER_SHORTLISTED,
        "reject": RECRUITER_REJECTED,
        "review": RECRUITER_REVIEWED,
        "hire": RECRUITER_HIRED,
    }
    return mapping[action]

