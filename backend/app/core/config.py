from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_JWT_SECRET = "change-me-in-development-only-min-32b"


class Settings(BaseSettings):
    """Environment-based application settings. Secrets come from env, never from code."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://recs:recs@localhost:5432/recs"
    test_database_url: str = "postgresql+psycopg://recs:recs@localhost:5432/recs_test"
    jwt_secret: str = INSECURE_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    ranker_impl: str = "baseline"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Application encoder identity. Not a Hugging Face revision SHA.
    embedding_model_version: str = "all-minilm-l6-v2-v1"
    # Optional Hugging Face snapshot/revision. Empty means the library default; that is not a claimed SHA.
    embedding_model_revision: str = ""
    embedding_text_version: str = "embedding-text-v1"
    embedding_backend: str = "sentence_transformers"
    blob_root: str = "./storage"
    max_resume_bytes: int = 5 * 1024 * 1024
    document_parser_version: str = "document-parser-v1"
    nlp_pipeline_version: str = "nlp-v1"
    ontology_default_version: str = "seed-0.1"
    ontology_fuzzy_threshold: float = 0.92
    ontology_max_depth: int = 4
    environment: str = "development"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = 10
    rate_limit_register_per_minute: int = 5
    rate_limit_refresh_per_minute: int = 30
    candidate_visibility_mode: str = "applicants_and_opted_in"
    argon2_time_cost: int = 2
    argon2_memory_cost: int = 65536
    # Baseline composer weights. Heuristic starting values, not empirically optimal.
    feature_schema_version: str = "feature-schema-v1"
    match_weight_set_version: str = "baseline-weights-v1"
    match_weight_required: float = 0.60
    match_weight_preferred: float = 0.10
    match_weight_semantic: float = 0.15
    match_weight_experience: float = 0.10
    match_weight_education_project: float = 0.05
    project_evidence_cosine_threshold: float = 0.45
    experience_evidence_cosine_threshold: float = 0.45
    # Potential (gap closability) heuristics. Independent of current-match weights.
    potential_weight_set_version: str = "potential-weights-v1"
    potential_max_graph_distance: int = 2
    potential_weight_exact: float = 1.0
    potential_weight_child: float = 0.8
    potential_weight_parent: float = 0.5
    potential_weight_related: float = 0.6
    potential_weight_similar: float = 0.5
    potential_two_hop_factor: float = 0.5
    potential_component_graph: float = 0.40
    potential_component_adjacent: float = 0.20
    potential_component_projects: float = 0.15
    potential_component_experience: float = 0.15
    potential_component_certifications: float = 0.05
    potential_component_semantic: float = 0.05
    potential_semantic_cosine_threshold: float = 0.45

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def cookie_secure_enabled(self) -> bool:
        return self.cookie_secure or self.is_production()

    def cookie_samesite_value(self) -> str:
        value = self.cookie_samesite.lower()
        if value not in {"lax", "strict", "none"}:
            return "lax"
        return value

    def resolved_embedding_model_name(self) -> str:
        return (self.embedding_model_name or self.embedding_model or "").strip()

    def assert_secure_for_environment(self) -> None:
        if self.is_production() and self.jwt_secret in {INSECURE_JWT_SECRET, ""}:
            raise RuntimeError("JWT_SECRET must be set to a long random value in production.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
