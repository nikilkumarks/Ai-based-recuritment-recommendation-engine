"""Ontology service: seed, resolve, persist, admin. Not NLP and not matching."""

from __future__ import annotations

import hashlib
import json
import uuid

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, UnprocessableError
from app.models import (
    CandidateProfile,
    CandidateSkill,
    JobPreferredSkill,
    JobRequiredSkill,
    JobRequirement,
    OntologyVersion,
    Skill,
    SkillAlias,
    SkillRelation,
    User,
)
from app.models.enums import (
    AliasSource,
    OntologyVersionStatus,
    SkillAttributionSource,
    SkillRelationType,
    SkillStatus,
    UserRole,
)
from app.modules.identity import audit
from app.modules.identity.tokens import utcnow
from app.modules.nlp.repository import NlpRepository
from app.modules.ontology.graph import SkillGraph
from app.modules.ontology.normalize import normalize_lookup, slugify
from app.modules.ontology.policies import classify_relationship
from app.modules.ontology.repository import OntologyRepository
from app.modules.ontology.resolver import OntologyIndex, SkillRecord, resolve_skill
from app.modules.ontology.schemas import (
    AliasCreate,
    OntologyVersionView,
    RelationCreate,
    SkillCreate,
    SkillListResponse,
    SkillNormalizationResult,
    SkillRelationshipView,
    SkillView,
    ValidationReport,
    VersionCreate,
)
from app.modules.ontology.seed import seed_ontology
from app.modules.ontology.validation import parent_cycles

ONTOLOGY_SEEDED = "ontology_seeded"
ONTOLOGY_SKILL_CREATED = "ontology_skill_created"
ONTOLOGY_ALIAS_CREATED = "ontology_alias_created"
ONTOLOGY_RELATION_CREATED = "ontology_relation_created"
ONTOLOGY_VERSION_CREATED = "ontology_version_created"


class OntologyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OntologyRepository(db)
        self.nlp_repo = NlpRepository(db)

    def seed(self) -> OntologyVersionView:
        row = seed_ontology(self.db)
        audit.record_audit(
            self.db,
            action=ONTOLOGY_SEEDED,
            resource_type="ontology_version",
            resource_id=row.id,
            metadata={"version": row.version},
        )
        self.db.flush()
        return _version_view(row)

    def load_index(self, version: str | None = None) -> OntologyIndex | None:
        row = self.repo.version_by_name(version) if version else self.repo.active_version()
        if row is None:
            return None
        if row.graph_snapshot:
            return _index_from_snapshot(row)
        return _index_from_live(row, self.repo)

    def resolve_mention(
        self,
        mention: str,
        *,
        ontology_version: str | None = None,
        source_section: str | None = None,
        evidence: str | None = None,
        start: int | None = None,
        end: int | None = None,
        fuzzy_threshold: float | None = None,
    ) -> SkillNormalizationResult:
        index = self.load_index(ontology_version)
        if index is None:
            lookup = normalize_lookup(mention)
            return SkillNormalizationResult(
                raw_text=mention.strip(),
                normalized_text=lookup,
                resolution_type="unmatched",
                ontology_version=ontology_version or get_settings().ontology_default_version,
                normalization_confidence=0,
                needs_review=True,
                source_section=source_section,
                evidence=evidence or mention.strip(),
                start=start,
                end=end,
            )
        return resolve_skill(
            mention,
            index,
            source_section=source_section,
            evidence=evidence,
            start=start,
            end=end,
            fuzzy_threshold=fuzzy_threshold,
        )

    def resolve_mentions(
        self, mentions: list[dict], *, ontology_version: str | None = None
    ) -> list[SkillNormalizationResult]:
        return [
            self.resolve_mention(
                str(item.get("raw_text") or item.get("value") or ""),
                ontology_version=ontology_version,
                source_section=item.get("source_section"),
                evidence=item.get("evidence"),
                start=item.get("start"),
                end=item.get("end"),
            )
            for item in mentions
            if str(item.get("raw_text") or item.get("value") or "").strip()
        ]

    def annotate_latest_draft(self, candidate_id: uuid.UUID) -> None:
        profile = self.nlp_repo.latest_profile(candidate_id, status="draft")
        if profile is None:
            return
        self.annotate_profile(profile)

    def annotate_profile(self, profile: CandidateProfile) -> list[SkillNormalizationResult]:
        payload = dict(profile.extracted_payload or {})
        mentions = list(payload.get("skills") or [])
        results = self.resolve_mentions(mentions)
        payload["normalized_skills"] = [item.model_dump(mode="json") for item in results]
        index = self.load_index()
        payload["ontology_version"] = index.version if index else get_settings().ontology_default_version
        profile.extracted_payload = payload
        flag_modified(profile, "extracted_payload")
        self.db.flush()
        return results

    def annotate_job_requirement(self, requirement: JobRequirement) -> None:
        payload = dict(requirement.extracted_payload or {})
        required = self.resolve_mentions(list(payload.get("required_skills") or []))
        preferred = self.resolve_mentions(list(payload.get("preferred_skills") or []))
        payload["normalized_required_skills"] = [item.model_dump(mode="json") for item in required]
        payload["normalized_preferred_skills"] = [item.model_dump(mode="json") for item in preferred]
        index = self.load_index()
        payload["ontology_version"] = index.version if index else get_settings().ontology_default_version
        requirement.extracted_payload = payload
        flag_modified(requirement, "extracted_payload")
        self.db.flush()

    def persist_confirmed_profile_skills(self, profile: CandidateProfile) -> None:
        payload = profile.extracted_payload or {}
        rows_data = payload.get("normalized_skills")
        if rows_data is None:
            self.annotate_profile(profile)
            payload = profile.extracted_payload or {}
            rows_data = payload.get("normalized_skills") or []
        grouped: dict[str, list[dict]] = {}
        for item in rows_data or []:
            skill_id = item.get("canonical_skill_id")
            if not skill_id or item.get("resolution_type") == "unmatched":
                continue
            grouped.setdefault(str(skill_id), []).append(item)
        rows = []
        version = payload.get("ontology_version")
        for skill_id, mentions in grouped.items():
            best = max(float(item.get("normalization_confidence") or 0) for item in mentions)
            rows.append(
                CandidateSkill(
                    candidate_profile_id=profile.id,
                    skill_id=uuid.UUID(skill_id),
                    source=SkillAttributionSource.CANDIDATE.value,
                    confidence=best,
                    evidence_span={
                        "ontology_version": version,
                        "mentions": mentions,
                    },
                )
            )
        self.repo.replace_candidate_skills(profile, rows)

    def persist_confirmed_job_skills(self, requirement: JobRequirement) -> None:
        payload = requirement.extracted_payload or {}
        if "normalized_required_skills" not in payload:
            self.annotate_job_requirement(requirement)
            payload = requirement.extracted_payload or {}
        required = _unique_skill_ids(payload.get("normalized_required_skills") or [])
        preferred = _unique_skill_ids(payload.get("normalized_preferred_skills") or [])
        self.repo.replace_job_skills(
            requirement,
            required=[
                JobRequiredSkill(job_requirement_id=requirement.id, skill_id=skill_id, importance="high")
                for skill_id in required
            ],
            preferred=[
                JobPreferredSkill(job_requirement_id=requirement.id, skill_id=skill_id, importance="normal")
                for skill_id in preferred
            ],
        )

    def classify(
        self, job_skill_id: uuid.UUID, candidate_skill_id: uuid.UUID
    ) -> SkillRelationshipView:
        index = self.load_index()
        if index is None:
            raise NotFoundError("No active ontology version.")
        job = index.skills.get(job_skill_id)
        cand = index.skills.get(candidate_skill_id)
        if job is None or cand is None:
            raise NotFoundError("Skill not found in the active ontology.")
        graph = index.graph(get_settings().ontology_max_depth)
        return classify_relationship(
            graph,
            job_skill_id=job.id,
            job_skill_name=job.canonical_name,
            candidate_skill_id=cand.id,
            candidate_skill_name=cand.canonical_name,
            ontology_version=index.version,
        )

    def list_skills(self) -> SkillListResponse:
        active = self.repo.active_version()
        return SkillListResponse(
            ontology_version=active.version if active else None,
            items=[_skill_view(item) for item in self.repo.list_skills()],
        )

    def list_versions(self) -> list[OntologyVersionView]:
        return [_version_view(item) for item in self.repo.list_versions()]

    def create_skill(self, user: User, payload: SkillCreate) -> SkillView:
        _require_admin(user)
        slug = payload.slug or slugify(payload.canonical_name)
        if self.repo.skill_by_slug(slug) is not None or self.repo.skill_by_name(payload.canonical_name):
            raise ConflictError("A canonical skill with that name or slug already exists.")
        skill = self.repo.add_skill(
            Skill(
                canonical_name=payload.canonical_name.strip(),
                slug=slug,
                description=payload.description,
                category=payload.category,
                status=SkillStatus.ACTIVE.value,
            )
        )
        audit.record_audit(
            self.db,
            action=ONTOLOGY_SKILL_CREATED,
            resource_type="skill",
            actor_user_id=user.id,
            resource_id=skill.id,
            metadata={"slug": skill.slug},
        )
        self.db.flush()
        return _skill_view(skill)

    def create_alias(self, user: User, payload: AliasCreate) -> dict:
        _require_admin(user)
        skill = self.repo.get_skill(payload.skill_id)
        if skill is None:
            raise NotFoundError("Skill not found.")
        normalized = normalize_lookup(payload.alias)
        if not normalized:
            raise UnprocessableError("Alias is empty after normalization.")
        if self.repo.alias_by_normalized(normalized) is not None:
            raise ConflictError("That alias already exists.")
        alias = self.repo.add_alias(
            SkillAlias(
                skill_id=skill.id,
                alias=payload.alias.strip(),
                normalized_alias=normalized,
                source=AliasSource.CURATED.value,
            )
        )
        audit.record_audit(
            self.db,
            action=ONTOLOGY_ALIAS_CREATED,
            resource_type="skill_alias",
            actor_user_id=user.id,
            resource_id=alias.id,
            metadata={"skill_id": str(skill.id)},
        )
        self.db.flush()
        return {"id": str(alias.id), "normalized_alias": normalized, "skill_id": str(skill.id)}

    def create_relation(self, user: User, payload: RelationCreate) -> dict:
        _require_admin(user)
        if payload.source_skill_id == payload.target_skill_id:
            raise UnprocessableError("A skill cannot relate to itself.")
        source = self.repo.get_skill(payload.source_skill_id)
        target = self.repo.get_skill(payload.target_skill_id)
        if source is None or target is None:
            raise NotFoundError("Skill not found.")
        if self.repo.relation_edge(payload.source_skill_id, payload.target_skill_id, payload.relation):
            raise ConflictError("That relationship already exists.")
        if payload.relation == SkillRelationType.PARENT_OF.value:
            existing = [
                (row.source_skill_id, row.target_skill_id)
                for row in self.repo.list_relations()
                if row.relation == SkillRelationType.PARENT_OF.value
            ]
            errors = parent_cycles([*existing, (payload.source_skill_id, payload.target_skill_id)])
            if errors:
                raise UnprocessableError(errors[0])
        relation = self.repo.add_relation(
            SkillRelation(
                source_skill_id=payload.source_skill_id,
                target_skill_id=payload.target_skill_id,
                relation=payload.relation,
                weight=payload.weight,
            )
        )
        audit.record_audit(
            self.db,
            action=ONTOLOGY_RELATION_CREATED,
            resource_type="skill_relation",
            actor_user_id=user.id,
            resource_id=relation.id,
            metadata={"relation": payload.relation},
        )
        self.db.flush()
        return {
            "id": str(relation.id),
            "source_skill_id": str(relation.source_skill_id),
            "target_skill_id": str(relation.target_skill_id),
            "relation": relation.relation,
        }

    def create_version(self, user: User, payload: VersionCreate) -> OntologyVersionView:
        _require_admin(user)
        if self.repo.version_by_name(payload.version) is not None:
            raise ConflictError("That ontology version already exists.")
        snapshot = self.repo.snapshot_payload()
        checksum = hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()
        if payload.activate:
            self.repo.retire_active()
        row = self.repo.add_version(
            OntologyVersion(
                version=payload.version,
                checksum=checksum,
                status=(
                    OntologyVersionStatus.ACTIVE.value
                    if payload.activate
                    else OntologyVersionStatus.DRAFT.value
                ),
                activated_at=utcnow() if payload.activate else None,
                graph_snapshot=snapshot,
            )
        )
        audit.record_audit(
            self.db,
            action=ONTOLOGY_VERSION_CREATED,
            resource_type="ontology_version",
            actor_user_id=user.id,
            resource_id=row.id,
            metadata={"version": row.version, "activated": payload.activate},
        )
        self.db.flush()
        return _version_view(row)

    def validate(self) -> ValidationReport:
        errors: list[str] = []
        names = [item.canonical_name for item in self.repo.list_skills()]
        seen: set[str] = set()
        for name in names:
            key = name.casefold()
            if key in seen:
                errors.append(f"Duplicate canonical skill: {name}")
            seen.add(key)
        aliases = [item.normalized_alias for item in self.repo.list_aliases()]
        alias_seen: set[str] = set()
        for alias in aliases:
            if alias in alias_seen:
                errors.append(f"Duplicate alias: {alias}")
            alias_seen.add(alias)
        parent_edges = [
            (row.source_skill_id, row.target_skill_id)
            for row in self.repo.list_relations()
            if row.relation == SkillRelationType.PARENT_OF.value
        ]
        errors.extend(parent_cycles(parent_edges))
        return ValidationReport(ok=not errors, errors=errors)

    def graph(self) -> SkillGraph | None:
        index = self.load_index()
        if index is None:
            return None
        return index.graph(get_settings().ontology_max_depth)


def _require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN.value:
        raise ForbiddenError("Only administrators can modify the ontology.")


def _unique_skill_ids(items: list[dict]) -> list[uuid.UUID]:
    seen: set[str] = set()
    ordered: list[uuid.UUID] = []
    for item in items:
        skill_id = item.get("canonical_skill_id")
        if not skill_id or item.get("resolution_type") == "unmatched":
            continue
        key = str(skill_id)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(uuid.UUID(key))
    return ordered


def _skill_view(skill: Skill) -> SkillView:
    return SkillView(
        id=skill.id,
        canonical_name=skill.canonical_name,
        slug=skill.slug,
        description=skill.description,
        category=skill.category,
        status=skill.status,
    )


def _version_view(row: OntologyVersion) -> OntologyVersionView:
    return OntologyVersionView(
        id=row.id,
        version=row.version,
        checksum=row.checksum,
        status=row.status,
        activated_at=row.activated_at,
    )


def _index_from_snapshot(row: OntologyVersion) -> OntologyIndex:
    data = row.graph_snapshot or {}
    skills: dict[uuid.UUID, SkillRecord] = {}
    canonical: dict[str, uuid.UUID] = {}
    fuzzy: list[tuple[str, uuid.UUID]] = []
    for item in data.get("skills") or []:
        skill_id = uuid.UUID(item["id"])
        lookup = normalize_lookup(item["canonical_name"])
        record = SkillRecord(
            id=skill_id,
            canonical_name=item["canonical_name"],
            slug=item["slug"],
            status=item.get("status") or SkillStatus.ACTIVE.value,
            lookup=lookup,
        )
        skills[skill_id] = record
        if record.status == SkillStatus.ACTIVE.value:
            canonical[lookup] = skill_id
            fuzzy.append((lookup, skill_id))
    exact_alias: dict[str, uuid.UUID] = {}
    normalized_alias: dict[str, uuid.UUID] = {}
    for item in data.get("aliases") or []:
        skill_id = uuid.UUID(item["skill_id"])
        exact_alias[str(item["alias"]).casefold()] = skill_id
        normalized_alias[item["normalized_alias"]] = skill_id
        fuzzy.append((item["normalized_alias"], skill_id))
    children: dict[uuid.UUID, list[uuid.UUID]] = {}
    parents: dict[uuid.UUID, list[uuid.UUID]] = {}
    related: dict[uuid.UUID, list[uuid.UUID]] = {}
    similar: dict[uuid.UUID, list[uuid.UUID]] = {}
    for item in data.get("relations") or []:
        source = uuid.UUID(item["source_skill_id"])
        target = uuid.UUID(item["target_skill_id"])
        relation = item["relation"]
        if relation == SkillRelationType.PARENT_OF.value:
            children.setdefault(source, []).append(target)
            parents.setdefault(target, []).append(source)
        elif relation == SkillRelationType.SIMILAR_TO.value:
            similar.setdefault(source, []).append(target)
            similar.setdefault(target, []).append(source)
            related.setdefault(source, []).append(target)
            related.setdefault(target, []).append(source)
        elif relation == SkillRelationType.RELATED_TO.value:
            related.setdefault(source, []).append(target)
            related.setdefault(target, []).append(source)
    return OntologyIndex(
        version=row.version,
        checksum=row.checksum,
        skills=skills,
        canonical_lookup=canonical,
        exact_alias=exact_alias,
        normalized_alias=normalized_alias,
        children={key: tuple(value) for key, value in children.items()},
        parents={key: tuple(value) for key, value in parents.items()},
        related={key: tuple(value) for key, value in related.items()},
        similar={key: tuple(value) for key, value in similar.items()},
        fuzzy_choices=tuple(fuzzy),
    )


def _index_from_live(row: OntologyVersion, repo: OntologyRepository) -> OntologyIndex:
    class _Snapshot:
        version = row.version
        checksum = row.checksum
        graph_snapshot = repo.snapshot_payload()

    return _index_from_snapshot(_Snapshot())
