from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from app.models import (
    Candidate,
    CandidateProfile,
    Job,
    Organization,
    Skill,
    User,
)
from app.models.enums import (
    ConfirmationStatus,
    JobStatus,
    OrganizationStatus,
    SkillStatus,
    UserRole,
    UserStatus,
)

TEST_PASSWORD_HASH = "argon2id$v=19$m=65536,t=3,p=4$testhashnotreal"


def make_user(
    email: str,
    role: str = UserRole.CANDIDATE.value,
    status: str = UserStatus.ACTIVE.value,
) -> User:
    return User(
        email=email.lower(),
        password_hash=TEST_PASSWORD_HASH,
        role=role,
        status=status,
    )


def make_org(name: str = "Acme Hiring", slug: str = "acme-hiring") -> Organization:
    return Organization(name=name, slug=slug, status=OrganizationStatus.ACTIVE.value)


def make_candidate(user: User) -> Candidate:
    return Candidate(
        user=user,
        headline="Software engineer",
        location="Bengaluru",
        preferences={"preferred_roles": ["backend"], "job_types": ["full_time"]},
    )


def make_skill(name: str, slug: str | None = None) -> Skill:
    return Skill(
        canonical_name=name,
        slug=slug or name.lower().replace(" ", "-"),
        status=SkillStatus.ACTIVE.value,
        category="cs-it",
    )


def make_job(org: Organization, creator: User | None, title: str = "ML Engineer") -> Job:
    return Job(
        organization=org,
        created_by=creator.id if creator is not None else None,
        title=title,
        description_raw="Build ranking systems.",
        status=JobStatus.OPEN.value,
    )


def make_profile(candidate: Candidate) -> CandidateProfile:
    return CandidateProfile(
        candidate=candidate,
        profile_version=1,
        confirmation_status=ConfirmationStatus.CONFIRMED.value,
        confirmed_at=datetime.now(timezone.utc),
        summary="Confirmed profile",
    )


def token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def future(hours: int = 24) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=hours)
