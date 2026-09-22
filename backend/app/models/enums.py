"""String enums persisted as VARCHAR plus CHECK constraints (not native PG enums)."""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


class OrganizationStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class MembershipRole(str, enum.Enum):
    OWNER = "owner"
    RECRUITER = "recruiter"
    MEMBER = "member"


class ParseStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    NEEDS_OCR = "needs_ocr"


class ConfirmationStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"


class SkillStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class AliasSource(str, enum.Enum):
    CURATED = "curated"
    EXTRACTED = "extracted"
    IMPORT = "import"


class SkillRelationType(str, enum.Enum):
    PARENT_OF = "parent_of"
    RELATED_TO = "related_to"
    SIMILAR_TO = "similar_to"


class OntologyVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class SkillAttributionSource(str, enum.Enum):
    CANDIDATE = "candidate"
    EXTRACTION = "extraction"
    IMPORT = "import"
    ADMIN = "admin"


class JobStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    SELECTED = "selected"
    WITHDRAWN = "withdrawn"


class CandidateDecisionAction(str, enum.Enum):
    SAVE = "save"
    APPLY = "apply"
    DISMISS = "dismiss"


class RecruiterDecisionAction(str, enum.Enum):
    VIEW = "view"
    COMPARE = "compare"
    SHORTLIST = "shortlist"
    REJECT = "reject"
    REVIEW = "review"
    HIRE = "hire"


class ScoringMode(str, enum.Enum):
    BASELINE = "baseline"
    TRAINED = "trained"


class MlModelStatus(str, enum.Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    REJECTED = "rejected"
    RETIRED = "retired"


class TrainingRunStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingJobType(str, enum.Enum):
    RESUME_PARSE = "resume_parse"
    RESUME_NLP = "resume_nlp"
    RESUME_EMBED = "resume_embed"
    PROFILE_EMBED = "profile_embed"
    JOB_PARSE = "job_parse"
    JOB_EMBED = "job_embed"
    PROJECT_EMBED = "project_embed"
    EXPERIENCE_EMBED = "experience_embed"
    MATCH_BATCH = "match_batch"


class ProcessingJobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EmbeddingOwnerType(str, enum.Enum):
    PROFILE = "profile"
    JOB = "job"
    PROJECT = "project"
    EXPERIENCE = "experience"
    RESUME_CHUNK = "resume_chunk"
    JOB_REQUIREMENT = "job_requirement"
    SKILL = "skill"


def enum_values(enum_cls: type[enum.Enum]) -> tuple[str, ...]:
    return tuple(item.value for item in enum_cls)
