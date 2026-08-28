"""One-shot MiniLM + pgvector verification. Not a ranking benchmark."""

from __future__ import annotations

import time
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Embedding
from app.models.enums import EmbeddingOwnerType
from app.modules.embeddings.encoder import SentenceTransformerEncoder, reset_encoder
from app.modules.embeddings.hashing import content_hash
from app.modules.embeddings.similarity import cosine_similarity, require_dimension


def main() -> None:
    settings = get_settings()
    print("backend", settings.embedding_backend)
    print("model_name", settings.resolved_embedding_model_name())
    print("app_version", settings.embedding_model_version)
    print("revision", settings.embedding_model_revision or "library-default")

    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        ext = conn.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname='vector'")).one()
        print("pgvector", ext[0], ext[1])

    started = time.perf_counter()
    encoder = SentenceTransformerEncoder(
        model_name=settings.resolved_embedding_model_name(),
        model_version=settings.embedding_model_version,
        model_revision=settings.embedding_model_revision,
    )
    print("load_ok", True)
    print("dimension", encoder.dimensions)
    print("load_ms", int((time.perf_counter() - started) * 1000))

    probe = "Short embedding timing probe."
    started = time.perf_counter()
    probe_vec = encoder.encode(probe)
    print("encode_ms", int((time.perf_counter() - started) * 1000))
    require_dimension(probe_vec, encoder.dimensions)

    text_a = "Developed machine learning models for classification and regression."
    text_b = "Built predictive models using Python for supervised learning."
    text_c = "Designed React user interfaces."
    vec_a = encoder.encode(text_a)
    vec_b = encoder.encode(text_b)
    vec_c = encoder.encode(text_c)
    sim_ab = cosine_similarity(vec_a, vec_b)
    sim_ac = cosine_similarity(vec_a, vec_c)
    print("sim_ab", round(sim_ab, 6))
    print("sim_ac", round(sim_ac, 6))
    print("ab_gt_ac", sim_ab > sim_ac)

    row = Embedding(
        owner_type=EmbeddingOwnerType.PROFILE.value,
        owner_id=uuid.uuid4(),
        chunk_type="full",
        model_name=encoder.model_name,
        model_version=encoder.model_version,
        embedding_text_version="embedding-text-v1",
        dimensions=encoder.dimensions,
        content_hash=content_hash(text_a),
        vector=vec_a,
    )
    with Session(engine) as db:
        db.add(row)
        db.commit()
        db.refresh(row)
        loaded = list(row.vector)
        print("persisted_dim", len(loaded))
        print("persisted_model", row.model_name)
        print("persisted_version", row.model_version)
        print("persisted_text_version", row.embedding_text_version)
        require_dimension(loaded, encoder.dimensions)
        print("roundtrip_cosine", round(cosine_similarity(vec_a, loaded), 6))
        pg_sim = db.execute(
            text("SELECT (1 - (vector <=> CAST(:q AS vector))) FROM embeddings WHERE id = CAST(:id AS uuid)"),
            {"q": str(vec_a), "id": str(row.id)},
        ).scalar()
        print("pgvector_similarity", None if pg_sim is None else round(float(pg_sim), 6))
        db.execute(text("DELETE FROM embeddings WHERE id = CAST(:id AS uuid)"), {"id": str(row.id)})
        db.commit()

    rss = None
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    rss = line.split()[1]
                    break
    except OSError:
        pass
    print("vmrss_kb", rss)
    reset_encoder()


if __name__ == "__main__":
    main()
