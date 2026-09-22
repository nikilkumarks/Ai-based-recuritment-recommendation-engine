"""Descriptive analytics. Not model performance and not hiring success."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.models import DatasetSnapshot, User
from app.models.enums import UserRole
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import (
    CountItem,
    DatasetSnapshotDetail,
    DatasetSnapshotSummary,
    DistributionBucket,
    FunnelAnalytics,
    MlModelSummary,
    RecruiterMatchingAnalytics,
    RecruiterOverview,
    RecruiterSkillsAnalytics,
    SkillGapItem,
)
from app.modules.authorization.service import AuthorizationService
from app.modules.ml.registry import activate_model, get_model, list_models, public_model_payload, reject_model
from app.modules.ml.service import DatasetService


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AnalyticsRepository(db)
        self.authz = AuthorizationService(db)
        self.datasets = DatasetService(db)

    def recruiter_overview(self, user: User) -> RecruiterOverview:
        org_id = _recruiter_org(self.authz, user)
        job_ids = self.repo.job_ids(org_id)
        return _overview(self.repo, job_ids)

    def recruiter_skills(self, user: User) -> RecruiterSkillsAnalytics:
        org_id = _recruiter_org(self.authz, user)
        return _skills(self.repo, self.repo.job_ids(org_id))

    def recruiter_matching(self, user: User) -> RecruiterMatchingAnalytics:
        org_id = _recruiter_org(self.authz, user)
        return _matching(self.repo.latest_run_features(self.repo.job_ids(org_id)))

    def recruiter_funnel(self, user: User) -> FunnelAnalytics:
        overview = self.recruiter_overview(user)
        return FunnelAnalytics(
            jobs=overview.jobs,
            applications=overview.applications,
            reviewed=overview.review_count + overview.shortlist_count + overview.reject_count,
            shortlisted=overview.shortlist_count,
            rejected=overview.reject_count,
        )

    def admin_overview(self, user: User) -> RecruiterOverview:
        self.authz.require_roles(user, UserRole.ADMIN.value)
        return _overview(self.repo, self.repo.job_ids(None))

    def admin_skills(self, user: User) -> RecruiterSkillsAnalytics:
        self.authz.require_roles(user, UserRole.ADMIN.value)
        return _skills(self.repo, self.repo.job_ids(None))

    def candidate_overview(self, user: User, candidate_id: uuid.UUID) -> RecruiterMatchingAnalytics:
        if user.role == UserRole.CANDIDATE.value:
            self.authz.require_candidate_owner(user, candidate_id)
        elif user.role != UserRole.ADMIN.value:
            raise ForbiddenError("Not allowed to view this analytics resource.")
        return _matching(self.repo.candidate_run_features(candidate_id))

    def create_dataset(self, user: User) -> DatasetSnapshotDetail:
        self.authz.require_roles(user, UserRole.ADMIN.value)
        row = self.datasets.create_snapshot(actor_id=user.id)
        return _dataset_detail(row)

    def list_datasets(self, user: User) -> list[DatasetSnapshotSummary]:
        self.authz.require_roles(user, UserRole.ADMIN.value)
        return [_dataset_summary(row) for row in self.datasets.list_snapshots()]

    def get_dataset(self, user: User, snapshot_id: uuid.UUID) -> DatasetSnapshotDetail:
        self.authz.require_roles(user, UserRole.ADMIN.value)
        row = self.datasets.get_snapshot(snapshot_id)
        if row is None:
            raise NotFoundError("Dataset snapshot not found.")
        return _dataset_detail(row)

    def list_models(self, user: User) -> list[MlModelSummary]:
        self.authz.require_roles(user, UserRole.ADMIN.value)
        return [MlModelSummary(**public_model_payload(row)) for row in list_models(self.db)]

    def get_model(self, user: User, model_id: uuid.UUID) -> MlModelSummary:
        self.authz.require_roles(user, UserRole.ADMIN.value)
        row = get_model(self.db, model_id)
        if row is None:
            raise NotFoundError("Model not found.")
        return MlModelSummary(**public_model_payload(row))

    def activate_model(self, user: User, model_id: uuid.UUID) -> MlModelSummary:
        self.authz.require_roles(user, UserRole.ADMIN.value)
        row = activate_model(self.db, actor_id=user.id, model_id=model_id)
        return MlModelSummary(**public_model_payload(row))

    def reject_model(self, user: User, model_id: uuid.UUID) -> MlModelSummary:
        self.authz.require_roles(user, UserRole.ADMIN.value)
        row = reject_model(self.db, actor_id=user.id, model_id=model_id)
        return MlModelSummary(**public_model_payload(row))


def _recruiter_org(authz: AuthorizationService, user: User) -> uuid.UUID:
    authz.require_roles(user, UserRole.RECRUITER.value)
    org_ids = authz.recruiter_organization_ids(user)
    if not org_ids:
        raise ForbiddenError("This recruiter has no organization.")
    return org_ids[0]


def _overview(repo: AnalyticsRepository, job_ids: list[uuid.UUID]) -> RecruiterOverview:
    latest = repo.latest_decisions(job_ids)
    shortlist = sum(1 for item in latest if item.action == "shortlist")
    reject = sum(1 for item in latest if item.action == "reject")
    review = sum(1 for item in latest if item.action == "review")
    decided = shortlist + reject + review
    pairs = max(repo.count_match_candidates(job_ids), decided)
    return RecruiterOverview(
        jobs=len(job_ids),
        candidates=repo.count_match_candidates(job_ids),
        applications=repo.count_applications(job_ids),
        shortlist_count=shortlist,
        reject_count=reject,
        review_count=review,
        decision_rate=(decided / pairs) if pairs else None,
        shortlist_rate=(shortlist / decided) if decided else None,
    )


def _skills(repo: AnalyticsRepository, job_ids: list[uuid.UUID]) -> RecruiterSkillsAnalytics:
    demand = repo.skill_demand(job_ids, preferred=False)
    supply_map = dict(repo.candidate_supply(job_ids))
    missing = repo.explanation_skill_counts(job_ids, "missing_skill", "required_skill")
    adjacent = repo.explanation_skill_counts(job_ids, "related_skill", "required_skill")
    potential_adj = repo.explanation_skill_counts(job_ids, "potential_adjacent", "missing_skill")
    if not adjacent:
        adjacent = potential_adj
    missing_map = dict(missing)
    adjacent_map = dict(adjacent)
    gaps = [
        SkillGapItem(
            skill=name,
            required_jobs=required,
            candidate_supply=supply_map.get(name, 0),
            missing_comparisons=missing_map.get(name, 0),
            related_comparisons=adjacent_map.get(name, 0),
        )
        for name, required in demand
    ]
    return RecruiterSkillsAnalytics(
        required_demand=[CountItem(name=n, count=c) for n, c in demand],
        preferred_demand=[CountItem(name=n, count=c) for n, c in repo.skill_demand(job_ids, True)],
        candidate_supply=[CountItem(name=n, count=c) for n, c in repo.candidate_supply(job_ids)],
        top_missing_skills=[CountItem(name=n, count=c) for n, c in missing],
        top_adjacent_skills=[CountItem(name=n, count=c) for n, c in adjacent],
        gaps=gaps,
    )


def _matching(features: list[dict[str, Any]]) -> RecruiterMatchingAnalytics:
    return RecruiterMatchingAnalytics(
        current_match=_buckets([row.get("current_match") for row in features]),
        potential=_buckets([row.get("potential") for row in features]),
        required_skill_coverage=_buckets([row.get("required_skill_coverage") for row in features]),
        semantic_similarity=_buckets(
            [
                row.get("profile_job_cosine")
                for row in features
                if row.get("semantic_similarity_available")
            ]
        ),
    )


def _buckets(values: list[Any]) -> list[DistributionBucket]:
    edges = [
        (0.0, 0.25, "0.00-0.25"),
        (0.25, 0.50, "0.25-0.50"),
        (0.50, 0.75, "0.50-0.75"),
        (0.75, 1.01, "0.75-1.00"),
    ]
    counts = {label: 0 for _, _, label in edges}
    for value in values:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        for low, high, label in edges:
            if low <= number < high:
                counts[label] += 1
                break
    return [DistributionBucket(bucket=label, count=counts[label]) for _, _, label in edges]


def _dataset_summary(row: DatasetSnapshot) -> DatasetSnapshotSummary:
    manifest = row.manifest or {}
    return DatasetSnapshotSummary(
        id=str(row.id),
        name=row.name,
        created_at=row.created_at.isoformat() if row.created_at else None,
        row_count=row.row_count,
        positive_count=int(manifest.get("positive_count") or 0),
        negative_count=int(manifest.get("negative_count") or 0),
        excluded_count=int(manifest.get("excluded_count") or 0),
        label_policy_version=row.label_policy_version,
        feature_schema_versions=list(manifest.get("feature_schema_versions") or []),
        ontology_versions=list(manifest.get("ontology_versions") or []),
        embedding_versions=list(manifest.get("embedding_versions") or []),
        sufficient_for_training_experiment=bool(
            manifest.get("sufficient_for_training_experiment")
        ),
        trained=False,
    )


def _dataset_detail(row: DatasetSnapshot) -> DatasetSnapshotDetail:
    summary = _dataset_summary(row)
    manifest = row.manifest or {}
    return DatasetSnapshotDetail(
        **summary.model_dump(),
        description=row.description,
        checksum=row.checksum,
        exclusion_reasons=dict(manifest.get("exclusion_reasons") or {}),
        source_decision_range=dict(manifest.get("source_decision_range") or {}),
        rows=list(row.rows or []),
    )
