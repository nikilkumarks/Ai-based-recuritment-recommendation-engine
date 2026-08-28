"""Explicit skill lexicon. Mentions are raw spans, not canonical ontology IDs.

ML and Machine Learning stay distinct in this phase.
"""

from __future__ import annotations

# Longer phrases first when scanning. Keep this list conservative.
SKILL_LEXICON: tuple[str, ...] = (
    "Machine Learning",
    "Deep Learning",
    "Natural Language Processing",
    "Computer Vision",
    "Artificial Intelligence",
    "scikit-learn",
    "TensorFlow",
    "PyTorch",
    "FastAPI",
    "Next.js",
    "Node.js",
    "PostgreSQL",
    "Kubernetes",
    "JavaScript",
    "TypeScript",
    "CI/CD",
    "C++",
    "C#",
    "AWS",
    "GCP",
    ".NET",
    "SQL",
    "HTML",
    "CSS",
    "NLP",
    "ML",
    "AI",
    "Python",
    "React",
    "Docker",
    "Linux",
    "Git",
    "Java",
    "Go",
    "Rust",
    "Redis",
    "Kafka",
    "Spark",
    "Pandas",
    "NumPy",
    "XGBoost",
)


def surface_normalize(text: str) -> str:
    """Whitespace/case fold only. Does not map aliases such as ML → Machine Learning."""
    return " ".join(text.split()).casefold()
