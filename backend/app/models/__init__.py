"""SQLAlchemy persistence models. Do not return these from API routers."""

from app.models.applications import Application, CandidateDecision, RecruiterDecision
from app.models.base import Base
from app.models.candidates import (
    Candidate,
    CandidateProfile,
    CandidateSkill,
    CertificationItem,
    EducationItem,
    ExperienceItem,
    ExtractionRevision,
    ProjectItem,
    Resume,
)
from app.models.identity import Organization, OrganizationMember, RefreshSession, User
from app.models.intelligence import Embedding, FeatureSnapshot, MatchExplanation, MatchRun
from app.models.jobs import Job, JobPreferredSkill, JobRequiredSkill, JobRequirement
from app.models.ml import DatasetSnapshot, MlModel, MlTrainingRun
from app.models.ontology import OntologyVersion, Skill, SkillAlias, SkillRelation
from app.models.ops import AuditLog, ProcessingJob

__all__ = [
    "Application",
    "AuditLog",
    "Base",
    "Candidate",
    "CandidateDecision",
    "CandidateProfile",
    "CandidateSkill",
    "CertificationItem",
    "DatasetSnapshot",
    "EducationItem",
    "Embedding",
    "ExperienceItem",
    "ExtractionRevision",
    "FeatureSnapshot",
    "Job",
    "JobPreferredSkill",
    "JobRequiredSkill",
    "JobRequirement",
    "MatchExplanation",
    "MatchRun",
    "MlModel",
    "MlTrainingRun",
    "OntologyVersion",
    "Organization",
    "OrganizationMember",
    "ProcessingJob",
    "ProjectItem",
    "RecruiterDecision",
    "RefreshSession",
    "Resume",
    "Skill",
    "SkillAlias",
    "SkillRelation",
    "User",
]
