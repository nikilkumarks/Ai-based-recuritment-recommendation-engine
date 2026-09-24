"""SQL aggregations for descriptive analytics. No model metrics."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models import (
    Application,
    CandidateProfile,
    CandidateSkill,
    FeatureSnapshot,
    Job,
    JobPreferredSkill,
    JobRequiredSkill,
    JobRequirement,
    MatchExplanation,
    MatchRun,
    RecruiterDecision,
    Skill,
)
from app.models.enums import ConfirmationStatus


class AnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def job_ids(self, organization_id: uuid.UUID | None) -> list[uuid.UUID]:
        stmt = select(Job.id)
        if organization_id is not None:
            stmt = stmt.where(Job.organization_id == organization_id)
        return list(self.db.scalars(stmt).all())

    def count_jobs(self, organization_id: uuid.UUID | None) -> int:
        stmt = select(func.count(Job.id))
        if organization_id is not None:
            stmt = stmt.where(Job.organization_id == organization_id)
        return int(self.db.scalar(stmt) or 0)

    def count_applications(self, job_ids: list[uuid.UUID]) -> int:
        if not job_ids:
            return 0
        return int(
            self.db.scalar(select(func.count(Application.id)).where(Application.job_id.in_(job_ids)))
            or 0
        )

    def count_match_candidates(self, job_ids: list[uuid.UUID]) -> int:
        if not job_ids:
            return 0
        return int(
            self.db.scalar(
                select(func.count(distinct(MatchRun.candidate_id))).where(MatchRun.job_id.in_(job_ids))
            )
            or 0
        )

    def latest_decisions(self, job_ids: list[uuid.UUID]) -> list[RecruiterDecision]:
        if not job_ids:
            return []
        rows = list(
            self.db.scalars(
                select(RecruiterDecision)
                .where(RecruiterDecision.job_id.in_(job_ids))
                .order_by(
                    RecruiterDecision.candidate_id,
                    RecruiterDecision.job_id,
                    RecruiterDecision.created_at.desc(),
                    RecruiterDecision.id.desc(),
                )
            ).all()
        )
        latest: dict[tuple[uuid.UUID, uuid.UUID], RecruiterDecision] = {}
        for row in rows:
            latest.setdefault((row.candidate_id, row.job_id), row)
        return list(latest.values())

    def skill_demand(self, job_ids: list[uuid.UUID], preferred: bool) -> list[tuple[str, int]]:
        if not job_ids:
            return []
        table = JobPreferredSkill if preferred else JobRequiredSkill
        stmt = (
            select(Skill.canonical_name, func.count(distinct(Job.id)))
            .join(table, table.skill_id == Skill.id)
            .join(JobRequirement, table.job_requirement_id == JobRequirement.id)
            .join(Job, JobRequirement.job_id == Job.id)
            .where(
                Job.id.in_(job_ids),
                JobRequirement.confirmation_status == ConfirmationStatus.CONFIRMED.value,
            )
            .group_by(Skill.canonical_name)
            .order_by(func.count(distinct(Job.id)).desc(), Skill.canonical_name)
            .limit(20)
        )
        return [(name, int(count)) for name, count in self.db.execute(stmt).all()]

    def candidate_supply(self, job_ids: list[uuid.UUID]) -> list[tuple[str, int]]:
        if not job_ids:
            return []
        candidates = select(distinct(MatchRun.candidate_id)).where(MatchRun.job_id.in_(job_ids))
        latest = (
            select(
                CandidateProfile.candidate_id,
                func.max(CandidateProfile.profile_version).label("version"),
            )
            .where(
                CandidateProfile.candidate_id.in_(candidates),
                CandidateProfile.confirmation_status == ConfirmationStatus.CONFIRMED.value,
            )
            .group_by(CandidateProfile.candidate_id)
            .subquery()
        )
        stmt = (
            select(Skill.canonical_name, func.count(distinct(CandidateProfile.candidate_id)))
            .select_from(CandidateSkill)
            .join(CandidateProfile, CandidateSkill.candidate_profile_id == CandidateProfile.id)
            .join(
                latest,
                (latest.c.candidate_id == CandidateProfile.candidate_id)
                & (latest.c.version == CandidateProfile.profile_version),
            )
            .join(Skill, CandidateSkill.skill_id == Skill.id)
            .group_by(Skill.canonical_name)
            .order_by(func.count(distinct(CandidateProfile.candidate_id)).desc(), Skill.canonical_name)
            .limit(20)
        )
        return [(name, int(count)) for name, count in self.db.execute(stmt).all()]

    def explanation_skill_counts(
        self, job_ids: list[uuid.UUID], trace_type: str, field: str
    ) -> list[tuple[str, int]]:
        if not job_ids:
            return []
        latest = (
            select(
                MatchRun.candidate_id,
                MatchRun.job_id,
                func.max(MatchRun.created_at).label("created_at"),
            )
            .where(MatchRun.job_id.in_(job_ids))
            .group_by(MatchRun.candidate_id, MatchRun.job_id)
            .subquery()
        )
        stmt = (
            select(MatchExplanation.traces)
            .join(MatchRun, MatchExplanation.match_run_id == MatchRun.id)
            .join(
                latest,
                (latest.c.candidate_id == MatchRun.candidate_id)
                & (latest.c.job_id == MatchRun.job_id)
                & (latest.c.created_at == MatchRun.created_at),
            )
        )
        counts: dict[str, int] = defaultdict(int)
        for traces in self.db.scalars(stmt).all():
            for item in traces or []:
                if item.get("type") != trace_type:
                    continue
                name = item.get(field) or item.get("required_skill") or item.get("skill")
                if name:
                    counts[str(name)] += 1
        return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:20]

    def latest_run_features(self, job_ids: list[uuid.UUID]) -> list[dict[str, Any]]:
        if not job_ids:
            return []
        latest = (
            select(
                MatchRun.candidate_id,
                MatchRun.job_id,
                func.max(MatchRun.created_at).label("created_at"),
            )
            .where(MatchRun.job_id.in_(job_ids))
            .group_by(MatchRun.candidate_id, MatchRun.job_id)
            .subquery()
        )
        stmt = (
            select(FeatureSnapshot.features)
            .join(MatchRun, FeatureSnapshot.match_run_id == MatchRun.id)
            .join(
                latest,
                (latest.c.candidate_id == MatchRun.candidate_id)
                & (latest.c.job_id == MatchRun.job_id)
                & (latest.c.created_at == MatchRun.created_at),
            )
        )
        return [row or {} for row in self.db.scalars(stmt).all()]

    def candidate_run_features(self, candidate_id: uuid.UUID) -> list[dict[str, Any]]:
        stmt = (
            select(FeatureSnapshot.features)
            .join(MatchRun, FeatureSnapshot.match_run_id == MatchRun.id)
            .where(MatchRun.candidate_id == candidate_id)
        )
        return [row or {} for row in self.db.scalars(stmt).all()]

    def list_all_users_with_orgs(self) -> list[tuple[Any, Any]]:
        from sqlalchemy.orm import selectinload
        from app.models import OrganizationMember, User

        stmt = (
            select(User, OrganizationMember)
            .outerjoin(OrganizationMember, User.id == OrganizationMember.user_id)
            .options(selectinload(OrganizationMember.organization))
            .order_by(User.created_at.desc())
        )
        return list(self.db.execute(stmt).all())

