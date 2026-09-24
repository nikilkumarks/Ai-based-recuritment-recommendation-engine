"""Persistence for recruiter decisions and point-in-time feature snapshots."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import FeatureSnapshot, Job, MatchRun, RecruiterDecision


class ApplicationsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_job(self, job_id: uuid.UUID) -> Job | None:
        return self.db.get(Job, job_id)

    def add_decision(self, row: RecruiterDecision) -> RecruiterDecision:
        self.db.add(row)
        self.db.flush()
        return row

    def list_decisions(self, job_id: uuid.UUID, candidate_id: uuid.UUID) -> list[RecruiterDecision]:
        return list(
            self.db.scalars(
                select(RecruiterDecision)
                .where(
                    RecruiterDecision.job_id == job_id,
                    RecruiterDecision.candidate_id == candidate_id,
                )
                .order_by(RecruiterDecision.created_at.asc(), RecruiterDecision.id.asc())
            ).all()
        )

    def latest_for_pairs(
        self, job_id: uuid.UUID, candidate_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, RecruiterDecision]:
        if not candidate_ids:
            return {}
        rows = list(
            self.db.scalars(
                select(RecruiterDecision)
                .where(
                    RecruiterDecision.job_id == job_id,
                    RecruiterDecision.candidate_id.in_(candidate_ids),
                )
                .order_by(RecruiterDecision.created_at.desc(), RecruiterDecision.id.desc())
            ).all()
        )
        latest: dict[uuid.UUID, RecruiterDecision] = {}
        for row in rows:
            latest.setdefault(row.candidate_id, row)
        return latest

    def snapshot_at_or_before(
        self,
        *,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
        when: datetime,
    ) -> FeatureSnapshot | None:
        """Latest snapshot with created_at <= when. Tie-break: created_at DESC, id DESC."""
        return self.db.scalar(
            select(FeatureSnapshot)
            .options(selectinload(FeatureSnapshot.match_run).selectinload(MatchRun.ontology_version))
            .join(MatchRun, FeatureSnapshot.match_run_id == MatchRun.id)
            .where(
                MatchRun.candidate_id == candidate_id,
                MatchRun.job_id == job_id,
                FeatureSnapshot.created_at <= when,
            )
            .order_by(FeatureSnapshot.created_at.desc(), FeatureSnapshot.id.desc())
            .limit(1)
        )

    def get_snapshot(self, snapshot_id: uuid.UUID) -> FeatureSnapshot | None:
        return self.db.scalar(
            select(FeatureSnapshot)
            .options(selectinload(FeatureSnapshot.match_run).selectinload(MatchRun.ontology_version))
            .where(FeatureSnapshot.id == snapshot_id)
        )

    def list_all_decisions(self) -> list[RecruiterDecision]:
        return list(
            self.db.scalars(
                select(RecruiterDecision).order_by(
                    RecruiterDecision.created_at.asc(), RecruiterDecision.id.asc()
                )
            ).all()
        )

    def scored_pairs(self) -> set[tuple[uuid.UUID, uuid.UUID]]:
        rows = self.db.execute(select(MatchRun.candidate_id, MatchRun.job_id).distinct()).all()
        return {(candidate_id, job_id) for candidate_id, job_id in rows}

    def get_application(self, candidate_id: uuid.UUID, job_id: uuid.UUID) -> Application | None:
        from app.models import Application

        return self.db.scalar(
            select(Application).where(
                Application.candidate_id == candidate_id,
                Application.job_id == job_id,
            )
        )

    def add_application(self, row: Application) -> Application:
        from app.models import Application

        self.db.add(row)
        self.db.flush()
        return row

    def list_candidate_applications(self, candidate_id: uuid.UUID) -> list[Application]:
        from app.models import Application

        return list(
            self.db.scalars(
                select(Application)
                .options(selectinload(Application.job))
                .where(Application.candidate_id == candidate_id)
                .order_by(Application.applied_at.desc())
            ).all()
        )

    def add_candidate_decision(self, row: CandidateDecision) -> CandidateDecision:
        from app.models import CandidateDecision

        self.db.add(row)
        self.db.flush()
        return row

    def get_latest_candidate_decision(
        self, candidate_id: uuid.UUID, job_id: uuid.UUID
    ) -> CandidateDecision | None:
        from app.models import CandidateDecision

        return self.db.scalar(
            select(CandidateDecision)
            .where(
                CandidateDecision.candidate_id == candidate_id,
                CandidateDecision.job_id == job_id,
            )
            .order_by(CandidateDecision.created_at.desc())
            .limit(1)
        )

    def list_candidate_decisions(self, candidate_id: uuid.UUID) -> list[CandidateDecision]:
        from app.models import CandidateDecision

        return list(
            self.db.scalars(
                select(CandidateDecision)
                .where(CandidateDecision.candidate_id == candidate_id)
                .order_by(CandidateDecision.created_at.desc())
            ).all()
        )

    def list_saved_jobs(self, candidate_id: uuid.UUID) -> list[Job]:
        from app.models import CandidateDecision, Job

        subq = (
            select(
                CandidateDecision.job_id,
                func.max(CandidateDecision.created_at).label("max_created"),
            )
            .where(CandidateDecision.candidate_id == candidate_id)
            .group_by(CandidateDecision.job_id)
            .subquery()
        )
        stmt = (
            select(Job)
            .join(
                CandidateDecision,
                (CandidateDecision.job_id == Job.id)
                & (CandidateDecision.candidate_id == candidate_id),
            )
            .join(
                subq,
                (subq.c.job_id == CandidateDecision.job_id)
                & (subq.c.max_created == CandidateDecision.created_at),
            )
            .where(CandidateDecision.action == "save")
            .order_by(CandidateDecision.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def applications_map_for_job(self, job_id: uuid.UUID) -> dict[uuid.UUID, Any]:
        from app.models import Application

        rows = list(
            self.db.scalars(
                select(Application).where(Application.job_id == job_id)
            ).all()
        )
        return {app.candidate_id: app for app in rows}

