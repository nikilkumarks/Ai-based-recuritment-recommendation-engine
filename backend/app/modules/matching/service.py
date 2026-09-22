"""Matching orchestrator. Baseline composer plus optional trained shortlist score."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.models import Candidate, CandidateProfile, CandidateSkill, Embedding, Job, JobRequirement, User
from app.models.enums import UserRole
from app.modules.applications.repository import ApplicationsRepository
from app.modules.authorization.service import AuthorizationService
from app.modules.embeddings.compatibility import (
    EncoderIdentity,
    classify_status,
    compatible,
    identity_from_row,
)
from app.modules.embeddings.encoder import get_encoder
from app.modules.embeddings.hashing import content_hash
from app.modules.embeddings.similarity import cosine_similarity
from app.modules.embeddings.text_builder import build_job_text, build_profile_text
from app.modules.embeddings.version import resolved_text_version
from app.modules.features.runtime import score_features
from app.modules.matching.composer import compose
from app.modules.matching.constants import (
    SCORING_MODE_BASELINE,
    SCORING_MODE_TRAINED,
    SNAPSHOT_FEATURE_SCHEMA_VERSION,
)
from app.modules.matching.evidence import (
    SkillEvidence,
    SkillRef,
    collect_preferred_evidence,
    collect_required_evidence,
)
from app.modules.matching.explain import extra_traces, skill_traces
from app.modules.matching.features import build_feature_snapshot
from app.modules.matching.gaps import required_gaps
from app.modules.matching.paths import suggested_paths_for_gaps
from app.modules.matching.policies import scoring_policy
from app.modules.matching.potential import assess_potential, potential_policy_from_settings
from app.modules.matching.repository import (
    EXPERIENCE_OWNER,
    HIDDEN_JOB_STATUSES,
    JOB_OWNER,
    PROFILE_OWNER,
    PROJECT_OWNER,
    MatchingRepository,
)
from app.modules.matching.schemas import (
    CandidateJobListResponse,
    CandidateJobMatchSummary,
    CounterfactualResult,
    GapItem,
    JobCandidateListResponse,
    JobCandidateMatchSummary,
    MatchResult,
    ScoreComponent,
    SkillMatchItem,
)
from app.modules.ontology.graph import SkillGraph
from app.modules.ontology.repository import OntologyRepository
from app.modules.ontology.resolver import OntologyIndex
from app.modules.ontology.service import OntologyService


class MatchingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = MatchingRepository(db)
        self.authz = AuthorizationService(db)
        self.decisions = ApplicationsRepository(db)
        self.ontology = OntologyService(db)
        self.ontology_repo = OntologyRepository(db)
        self._index: OntologyIndex | None = None
        self._encoder_identity: EncoderIdentity | None = None

    def list_jobs_for_candidate(self, *, user: User, candidate_id: uuid.UUID) -> CandidateJobListResponse:
        self._require_candidate_access(user, candidate_id)
        jobs = [
            job
            for job in self.repo.list_visible_jobs()
            if self._candidate_may_view_job(user, job)
        ]
        items: list[CandidateJobMatchSummary] = []
        context = self._load_context(candidate_id)
        for job in jobs:
            result = self._score_pair(context, job, persist=True, include_career_paths=False)
            items.append(
                CandidateJobMatchSummary(
                    job_id=job.id,
                    job_title=job.title,
                    current_match=result.current_match,
                    potential=result.potential,
                    potential_status=result.potential_status,
                    required_skill_coverage=result.required_skill_coverage,
                    missing_skills=result.missing_skills,
                    partial_skills=result.partial_skills,
                    related_skills=result.related_skills,
                    scoring_mode=result.scoring_mode,
                    model_version=result.model_version,
                    model_relevance_score=result.model_relevance_score,
                    semantic_similarity_available=result.semantic_similarity_available,
                    sort_note=(
                        "trained_model_relevance_desc"
                        if result.scoring_mode == SCORING_MODE_TRAINED
                        else "baseline_current_match_desc"
                    ),
                )
            )
        trained = all(row.scoring_mode == SCORING_MODE_TRAINED for row in items) and bool(items)
        items.sort(
            key=lambda row: _list_sort_key(row.scoring_mode, row.model_relevance_score, row.current_match)
        )
        return CandidateJobListResponse(
            items=items,
            scoring_mode=SCORING_MODE_TRAINED if trained else SCORING_MODE_BASELINE,
            sort=(
                "model_relevance_score DESC (trained shortlist score; baseline current_match retained)"
                if trained
                else "current_match DESC (baseline sorting, not a trained ranker)"
            ),
        )

    def match_detail(self, *, user: User, candidate_id: uuid.UUID, job_id: uuid.UUID) -> MatchResult:
        self._require_match_detail_access(user, candidate_id, job_id)
        job = self.repo.get_job(job_id)
        if job is None or not self._candidate_may_view_job(user, job):
            raise NotFoundError("Job not found.")
        context = self._load_context(candidate_id)
        include_paths = user.role in {UserRole.CANDIDATE.value, UserRole.ADMIN.value}
        return self._score_pair(context, job, persist=True, include_career_paths=include_paths)

    def list_candidates_for_job(self, *, user: User, job_id: uuid.UUID) -> JobCandidateListResponse:
        job = self.authz.require_job_org_access(user, job_id)
        loaded = self.repo.get_job(job.id)
        if loaded is None:
            raise NotFoundError("Job not found.")
        if self.repo.latest_confirmed_requirement(loaded) is None:
            raise ConflictError("This job has no confirmed requirements.")
        items: list[JobCandidateMatchSummary] = []
        scored: list[tuple] = []
        for candidate in self.repo.list_candidates():
            if not self.authz.can_recruiter_view_candidate(user, candidate):
                continue
            if self.repo.latest_confirmed_profile(candidate.id) is None:
                continue
            context = self._load_context(candidate.id)
            result = self._score_pair(context, loaded, persist=True, include_career_paths=False)
            identifier = candidate.user.email if candidate.user is not None else str(candidate.id)
            scored.append((candidate, result, identifier))
        latest = self.decisions.latest_for_pairs(job.id, [row[0].id for row in scored])
        for candidate, result, identifier in scored:
            current = latest.get(candidate.id)
            items.append(
                JobCandidateMatchSummary(
                    candidate_id=candidate.id,
                    identifier=identifier,
                    headline=candidate.headline,
                    current_match=result.current_match,
                    potential=result.potential,
                    potential_status=result.potential_status,
                    required_skill_coverage=result.required_skill_coverage,
                    missing_skills=result.missing_skills,
                    related_skills=result.related_skills,
                    scoring_mode=result.scoring_mode,
                    model_version=result.model_version,
                    model_relevance_score=result.model_relevance_score,
                    current_decision=current.action if current is not None else None,
                    sort_note=(
                        "trained_model_relevance_desc"
                        if result.scoring_mode == SCORING_MODE_TRAINED
                        else "baseline_current_match_desc"
                    ),
                )
            )
        trained = all(row.scoring_mode == SCORING_MODE_TRAINED for row in items) and bool(items)
        items.sort(
            key=lambda row: _list_sort_key(row.scoring_mode, row.model_relevance_score, row.current_match)
        )
        return JobCandidateListResponse(
            job_id=job.id,
            items=items,
            scoring_mode=SCORING_MODE_TRAINED if trained else SCORING_MODE_BASELINE,
            sort=(
                "model_relevance_score DESC (trained shortlist score; baseline current_match retained)"
                if trained
                else "current_match DESC (baseline sorting, not a trained ranker)"
            ),
        )

    def simulate_add_skill(
        self,
        *,
        user: User,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
        skill_id: uuid.UUID,
    ) -> CounterfactualResult:
        self._require_candidate_access(user, candidate_id)
        job = self.repo.get_job(job_id)
        if job is None or not self._candidate_may_view_job(user, job):
            raise NotFoundError("Job not found.")
        skill = self.repo.get_skill(skill_id)
        if skill is None:
            raise NotFoundError("Skill not found.")
        context = self._load_context(candidate_id)
        baseline = self._score_pair(context, job, persist=False, include_career_paths=False)
        simulated_skills = list(context.candidate_skills)
        if all(item.skill_id != skill_id for item in simulated_skills):
            simulated_skills.append(
                SkillRef(skill_id=skill.id, canonical_name=skill.canonical_name, mention=None)
            )
        simulated_context = MatchContext(
            candidate_id=context.candidate_id,
            profile=context.profile,
            candidate_skills=simulated_skills,
            index=context.index,
            graph=context.graph,
            potential_graph=context.potential_graph,
            ontology_version=context.ontology_version,
            ontology_version_id=context.ontology_version_id,
            encoder_identity=context.encoder_identity,
        )
        simulated = self._score_pair(simulated_context, job, persist=False, include_career_paths=False)
        potential_delta = None
        if baseline.potential is not None and simulated.potential is not None:
            potential_delta = round(simulated.potential - baseline.potential, 4)
        elif simulated.potential is not None:
            potential_delta = simulated.potential
        return CounterfactualResult(
            candidate_id=candidate_id,
            job_id=job_id,
            skill_id=skill.id,
            skill_name=skill.canonical_name,
            baseline_current_match=baseline.current_match,
            simulated_current_match=simulated.current_match,
            delta=round(simulated.current_match - baseline.current_match, 4),
            potential_before=baseline.potential,
            potential_after=simulated.potential,
            potential_delta=potential_delta,
            persisted=False,
            affected_evidence=[
                item.model_dump(mode="json")
                for item in simulated.matched_skills + simulated.partial_skills + simulated.related_skills
                if item.skill_id == skill.id or item.candidate_skill_id == skill.id
            ]
            + [
                item.model_dump(mode="json")
                for item in simulated.missing_skills
                if item.skill_id == skill.id
            ],
            affected_gaps=[
                item.model_dump(mode="json")
                for item in baseline.gaps + simulated.gaps
                if item.skill_id == skill.id
            ],
            scoring_mode="baseline",
            model_version=None,
        )

    def _require_candidate_access(self, user: User, candidate_id: uuid.UUID) -> Candidate:
        if user.role == UserRole.ADMIN.value:
            candidate = self.repo.get_candidate(candidate_id)
            if candidate is None:
                raise NotFoundError("Candidate not found.")
            return candidate
        return self.authz.require_candidate_owner(user, candidate_id)

    def _require_match_detail_access(self, user: User, candidate_id: uuid.UUID, job_id: uuid.UUID) -> None:
        if user.role == UserRole.ADMIN.value:
            if self.repo.get_candidate(candidate_id) is None:
                raise NotFoundError("Candidate not found.")
            return
        if user.role == UserRole.CANDIDATE.value:
            self.authz.require_candidate_owner(user, candidate_id)
            return
        if user.role == UserRole.RECRUITER.value:
            self.authz.require_job_org_access(user, job_id)
            self.authz.require_recruiter_candidate_scope(user, candidate_id)
            return
        raise ForbiddenError("You do not have permission to access this match.")

    def _candidate_may_view_job(self, user: User, job: Job) -> bool:
        if self.repo.latest_confirmed_requirement(job) is None:
            return False
        if user.role == UserRole.ADMIN.value:
            return True
        if user.role == UserRole.RECRUITER.value:
            return True
        return job.status not in HIDDEN_JOB_STATUSES

    def _load_context(self, candidate_id: uuid.UUID) -> MatchContext:
        profile = self.repo.latest_confirmed_profile(candidate_id)
        if profile is None:
            raise ConflictError("Confirm the candidate profile before matching.")
        index = self._ontology_index()
        active = self.ontology_repo.active_version()
        potential_depth = get_settings().potential_max_graph_distance
        return MatchContext(
            candidate_id=candidate_id,
            profile=profile,
            candidate_skills=_profile_skills(profile),
            index=index,
            graph=index.graph(get_settings().ontology_max_depth),
            potential_graph=index.graph(potential_depth),
            ontology_version=index.version,
            ontology_version_id=active.id if active is not None else None,
            encoder_identity=self._identity(),
        )

    def _ontology_index(self) -> OntologyIndex:
        if self._index is None:
            loaded = self.ontology.load_index()
            if loaded is None:
                raise ConflictError("No active ontology version.")
            self._index = loaded
        return self._index

    def _identity(self) -> EncoderIdentity:
        if self._encoder_identity is None:
            self._encoder_identity = get_encoder().identity(resolved_text_version())
        return self._encoder_identity

    def _score_pair(
        self,
        context: MatchContext,
        job: Job,
        *,
        persist: bool,
        include_career_paths: bool,
    ) -> MatchResult:
        requirement = self.repo.latest_confirmed_requirement(job)
        if requirement is None:
            raise ConflictError("This job has no confirmed requirements.")
        policy = scoring_policy()
        required_refs = _job_required(requirement)
        preferred_refs = _job_preferred(requirement)
        required = collect_required_evidence(
            context.graph,
            required=required_refs,
            candidate_skills=context.candidate_skills,
            ontology_version=context.ontology_version,
        )
        preferred = collect_preferred_evidence(
            context.graph,
            preferred=preferred_refs,
            candidate_skills=context.candidate_skills,
            ontology_version=context.ontology_version,
        )
        semantic = self._semantic_features(context, job, requirement)
        experience = _experience_features(
            context.profile, requirement, semantic, policy.experience_cosine_threshold
        )
        education = _education_features(context.profile, requirement)
        projects = _project_features(
            semantic, policy.project_cosine_threshold, len(context.profile.project_items)
        )
        embedding_meta = {
            "embedding_model_name": semantic.get("embedding_model_name"),
            "embedding_model_version": semantic.get("embedding_model_version"),
            "embedding_dimensions": semantic.get("embedding_dimensions"),
            "embedding_text_version": semantic.get("embedding_text_version"),
            "profile_embedding_status": semantic.get("profile_embedding_status"),
            "job_embedding_status": semantic.get("job_embedding_status"),
        }
        features = build_feature_snapshot(
            candidate_id=context.candidate_id,
            job_id=job.id,
            ontology_version=context.ontology_version,
            policy=policy,
            required=required,
            preferred=preferred,
            embedding_meta=embedding_meta,
            semantic={
                "profile_job_cosine": semantic.get("profile_job_cosine"),
                "semantic_similarity_available": semantic.get("semantic_similarity_available"),
                "relevant_project_cosine": semantic.get("relevant_project_cosine"),
                "relevant_experience_cosine": semantic.get("relevant_experience_cosine"),
            },
            experience=experience,
            education=education,
            projects=projects,
        )
        composed = compose(features, policy)
        current_before_potential = composed.current_match
        potential_policy = potential_policy_from_settings()
        potential = assess_potential(
            graph=context.potential_graph,
            index=context.index,
            ontology_version=context.ontology_version,
            required=required,
            preferred=preferred,
            candidate_skills=context.candidate_skills,
            profile=context.profile,
            policy=potential_policy,
            semantic=semantic,
        )
        features.update(potential.features)
        features["current_match"] = current_before_potential
        embedding_identity = None
        if features.get("embedding_model_name"):
            embedding_identity = (
                f"{features.get('embedding_model_name')}|"
                f"{features.get('embedding_model_version')}|"
                f"{features.get('embedding_text_version')}"
            )
        inference = score_features(
            self.db,
            features,
            ontology_version=context.ontology_version,
            embedding_identity=embedding_identity,
        )
        features["scoring_mode"] = inference.scoring_mode
        features["model_version"] = inference.model_version
        features["model_relevance_score"] = inference.model_relevance_score
        features["fallback_reason"] = inference.fallback_reason
        features["feature_schema_version"] = SNAPSHOT_FEATURE_SCHEMA_VERSION
        traces = (
            skill_traces(
                required=required,
                preferred=preferred,
                ontology_version=context.ontology_version,
            )
            + extra_traces(
                semantic_available=bool(features["semantic_similarity_available"]),
                semantic_similarity=features.get("profile_job_cosine"),  # type: ignore[arg-type]
                experience_satisfied=features.get("experience_satisfied"),  # type: ignore[arg-type]
                required_experience_years=features.get("required_experience_years"),  # type: ignore[arg-type]
                candidate_experience_years=features.get("candidate_experience_years"),  # type: ignore[arg-type]
                education_requirement_present=bool(features.get("education_requirement_present")),
                education_alignment=features.get("education_alignment"),  # type: ignore[arg-type]
                relevant_project_count=int(features.get("relevant_project_count") or 0),
                project_evidence_present=bool(features.get("project_evidence_present")),
            )
            + list(potential.traces)
        )
        if inference.fallback_reason:
            traces.append(
                {
                    "type": "ml_fallback",
                    "reason": inference.fallback_reason,
                    "note": "Recommendations used baseline matching; trained model unavailable.",
                }
            )
        traces.extend(inference.ml_explanations)
        paths: list[dict[str, Any]] = []
        if include_career_paths:
            paths = suggested_paths_for_gaps(
                graph=context.potential_graph,
                index=context.index,
                gaps=potential.gaps,
                candidate_skills=context.candidate_skills,
                max_distance=potential_policy.max_graph_distance,
            )
        run_id = None
        created_at = None
        if persist:
            run = self.repo.persist_run(
                candidate_id=context.candidate_id,
                job_id=job.id,
                ontology_version_id=context.ontology_version_id,
                feature_schema_version=SNAPSHOT_FEATURE_SCHEMA_VERSION,
                weight_set_version=policy.weight_set_version,
                current_match=current_before_potential,
                potential=potential.potential,
                semantic_similarity=features.get("profile_job_cosine"),  # type: ignore[arg-type]
                project_relevance=features.get("relevant_project_cosine"),  # type: ignore[arg-type]
                experience_relevance=features.get("relevant_experience_cosine"),  # type: ignore[arg-type]
                features=features,
                traces=traces,
                scoring_mode=inference.scoring_mode,
                model_version=inference.model_version,
            )
            run_id = run.id
            created_at = run.created_at
        cosine = features.get("profile_job_cosine")
        return MatchResult(
            candidate_id=context.candidate_id,
            job_id=job.id,
            current_match=current_before_potential,
            potential=potential.potential,
            potential_status=potential.status,
            potential_components={
                item.name: item.value if item.available else None for item in potential.components
            },
            suggested_skill_paths=paths,
            semantic_similarity=float(cosine) if isinstance(cosine, (int, float)) else None,
            semantic_similarity_available=bool(features["semantic_similarity_available"]),
            scoring_mode=inference.scoring_mode,
            model_version=inference.model_version,
            model_relevance_score=inference.model_relevance_score,
            ml_explanations=inference.ml_explanations,
            fallback_reason=inference.fallback_reason,
            feature_schema_version=SNAPSHOT_FEATURE_SCHEMA_VERSION,
            ontology_version=context.ontology_version,
            weight_set_version=policy.weight_set_version,
            required_skill_coverage=float(features["required_skill_coverage"]),
            preferred_skill_coverage=float(features["preferred_skill_coverage"]),
            matched_skills=_skill_items(required, "exact"),
            partial_skills=_skill_items(required, "child") + _skill_items(required, "parent"),
            related_skills=_skill_items(required, "related"),
            missing_skills=_skill_items(required, "missing"),
            gaps=[
                GapItem(skill=item["skill"], skill_id=uuid.UUID(item["skill_id"]), type=item["type"])
                for item in required_gaps(required)
            ],
            explanations=traces,
            components=[
                ScoreComponent(
                    name=item.name,
                    value=item.value,
                    weight=item.weight,
                    available=item.available,
                )
                for item in composed.components
            ],
            match_run_id=run_id,
            created_at=created_at,
        )

    def _semantic_features(
        self,
        context: MatchContext,
        job: Job,
        requirement: JobRequirement,
    ) -> dict[str, Any]:
        identity = context.encoder_identity
        profile_text = build_profile_text(context.profile)
        job_text = build_job_text(job, requirement)
        profile_row = self.repo.latest_owner_embedding(PROFILE_OWNER, context.profile.id)
        job_row = self.repo.latest_owner_embedding(JOB_OWNER, job.id)
        profile_status = classify_status(
            row=profile_row, current=identity, content_hash=content_hash(profile_text)
        )
        job_status = classify_status(row=job_row, current=identity, content_hash=content_hash(job_text))
        payload: dict[str, Any] = {
            "embedding_model_name": identity.model_name,
            "embedding_model_version": identity.model_version,
            "embedding_dimensions": identity.dimensions,
            "embedding_text_version": identity.embedding_text_version,
            "profile_embedding_status": profile_status,
            "job_embedding_status": job_status,
            "semantic_similarity_available": False,
            "profile_job_cosine": None,
            "relevant_project_cosine": None,
            "relevant_experience_cosine": None,
            "experience_item_cosines": [],
            "project_item_cosines": [],
        }
        if (
            profile_row is not None
            and job_row is not None
            and profile_status == "current"
            and job_status == "current"
            and compatible(identity_from_row(profile_row), identity_from_row(job_row))
        ):
            cosine = cosine_similarity(list(profile_row.vector), list(job_row.vector))
            payload["semantic_similarity_available"] = True
            payload["profile_job_cosine"] = round(float(cosine), 5)
            payload["embedding_model_name"] = profile_row.model_name
            payload["embedding_model_version"] = profile_row.model_version
            payload["embedding_dimensions"] = profile_row.dimensions
            payload["embedding_text_version"] = profile_row.embedding_text_version
            job_identity = identity_from_row(job_row)
            payload["relevant_experience_cosine"], payload["experience_item_cosines"] = _item_cosines(
                self.repo,
                owner_type=EXPERIENCE_OWNER,
                owner_ids=[item.id for item in context.profile.experience_items],
                job_row=job_row,
                job_identity=job_identity,
            )
            payload["relevant_project_cosine"], payload["project_item_cosines"] = _item_cosines(
                self.repo,
                owner_type=PROJECT_OWNER,
                owner_ids=[item.id for item in context.profile.project_items],
                job_row=job_row,
                job_identity=job_identity,
            )
        return payload


class MatchContext:
    def __init__(
        self,
        *,
        candidate_id: uuid.UUID,
        profile: CandidateProfile,
        candidate_skills: list[SkillRef],
        index: OntologyIndex,
        graph: SkillGraph,
        potential_graph: SkillGraph,
        ontology_version: str,
        ontology_version_id: uuid.UUID | None,
        encoder_identity: EncoderIdentity,
    ) -> None:
        self.candidate_id = candidate_id
        self.profile = profile
        self.candidate_skills = candidate_skills
        self.index = index
        self.graph = graph
        self.potential_graph = potential_graph
        self.ontology_version = ontology_version
        self.ontology_version_id = ontology_version_id
        self.encoder_identity = encoder_identity


def _profile_skills(profile: CandidateProfile) -> list[SkillRef]:
    refs: list[SkillRef] = []
    for row in profile.skills:
        mention, resolution = _mention_from_skill(row)
        name = row.skill.canonical_name if row.skill is not None else str(row.skill_id)
        refs.append(
            SkillRef(
                skill_id=row.skill_id,
                canonical_name=name,
                mention=mention,
                resolution_type=resolution,
            )
        )
    return refs


def _mention_from_skill(row: CandidateSkill) -> tuple[str | None, str | None]:
    span = row.evidence_span or {}
    mentions = span.get("mentions") or []
    if not mentions:
        return None, None
    alias = next((item for item in mentions if (item.get("resolution_type") or "") == "alias"), None)
    chosen = alias or mentions[0]
    return chosen.get("raw_text"), chosen.get("resolution_type")


def _job_required(requirement: JobRequirement) -> list[SkillRef]:
    return [
        SkillRef(
            skill_id=row.skill_id,
            canonical_name=row.skill.canonical_name if row.skill is not None else str(row.skill_id),
        )
        for row in requirement.required_skills
    ]


def _job_preferred(requirement: JobRequirement) -> list[SkillRef]:
    return [
        SkillRef(
            skill_id=row.skill_id,
            canonical_name=row.skill.canonical_name if row.skill is not None else str(row.skill_id),
        )
        for row in requirement.preferred_skills
    ]


def _skill_items(items: list[SkillEvidence], kind: str) -> list[SkillMatchItem]:
    return [
        SkillMatchItem(
            skill_id=item.job_skill_id,
            skill=item.job_skill_name,
            evidence_type=item.kind,
            candidate_skill_id=item.candidate_skill_id,
            candidate_evidence=item.candidate_mention,
            hops=item.hops,
        )
        for item in items
        if item.kind == kind
    ]


def _experience_features(
    profile: CandidateProfile,
    requirement: JobRequirement,
    semantic: dict[str, Any],
    threshold: float,
) -> dict[str, Any]:
    required_years = _float_or_none(requirement.min_years_experience)
    candidate_years = _candidate_years(profile)
    satisfied: bool | None
    if required_years is None:
        satisfied = True
    elif candidate_years is None:
        satisfied = None
    else:
        satisfied = candidate_years >= required_years
    relevant = False
    cosine = semantic.get("relevant_experience_cosine")
    if isinstance(cosine, (int, float)) and cosine >= threshold:
        relevant = True
    return {
        "candidate_experience_years": candidate_years,
        "required_experience_years": required_years,
        "experience_satisfied": satisfied,
        "experience_evidence_present": relevant,
    }


def _candidate_years(profile: CandidateProfile) -> float | None:
    items = list(profile.experience_items)
    if not items:
        return None
    years: list[float] = []
    for item in items:
        if item.years_experience is None:
            return None
        years.append(float(item.years_experience))
    return round(sum(years), 2)


def _education_features(profile: CandidateProfile, requirement: JobRequirement) -> dict[str, Any]:
    required = (requirement.education_level or "").strip()
    present = bool(required)
    if not present:
        return {"education_requirement_present": False, "education_alignment": None}
    levels = [(item.education_level or "").strip() for item in profile.education_items]
    known = [value for value in levels if value]
    if not known:
        return {"education_requirement_present": True, "education_alignment": None}
    target = required.casefold()
    aligned = any(value.casefold() == target for value in known)
    return {"education_requirement_present": True, "education_alignment": aligned}


def _project_features(semantic: dict[str, Any], threshold: float, project_count: int) -> dict[str, Any]:
    cosine = semantic.get("relevant_project_cosine")
    relevant = 0
    present = False
    if isinstance(cosine, (int, float)):
        present = True
        if cosine >= threshold:
            relevant = 1
    elif project_count > 0 and semantic.get("semantic_similarity_available"):
        present = False
    return {
        "candidate_project_count": project_count,
        "relevant_project_count": relevant,
        "project_evidence_present": present and relevant > 0,
        "relevant_project_cosine": cosine if isinstance(cosine, (int, float)) else None,
    }


def _item_cosines(
    repo: MatchingRepository,
    *,
    owner_type: str,
    owner_ids: list[uuid.UUID],
    job_row: Embedding,
    job_identity: EncoderIdentity,
) -> tuple[float | None, list[float]]:
    rows = repo.latest_embeddings_for_owners(owner_type, owner_ids)
    values: list[float] = []
    job_vector = list(job_row.vector)
    for row in rows.values():
        stored = identity_from_row(row)
        if not compatible(stored, job_identity):
            continue
        values.append(round(float(cosine_similarity(list(row.vector), job_vector)), 5))
    if not values:
        return None, []
    return max(values), values


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _list_sort_key(
    scoring_mode: str, model_relevance_score: float | None, current_match: float
) -> tuple[float, float]:
    if scoring_mode == SCORING_MODE_TRAINED and model_relevance_score is not None:
        return (-model_relevance_score, -current_match)
    return (0.0, -current_match)

