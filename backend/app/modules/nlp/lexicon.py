"""Explicit skill lexicon. Mentions are raw spans, not canonical ontology IDs.

ML and Machine Learning stay distinct in this phase.
"""

from __future__ import annotations

# Longer phrases first when scanning. Keep this list conservative.
SKILL_LEXICON: tuple[str, ...] = (
    "Natural Language Processing",
    "Data Structures & Algorithms",
    "Object-Oriented Programming",
    "Artificial Intelligence",
    "Machine Learning",
    "Deep Learning",
    "Computer Vision",
    "Tailwind CSS",
    "scikit-learn",
    "RESTful APIs",
    "Express.js",
    "React Native",
    "MERN Stack",
    "TensorFlow",
    "PostgreSQL",
    "Kubernetes",
    "JavaScript",
    "TypeScript",
    "Cohere AI",
    "Hugging Face",
    "Google OAuth",
    "REST APIs",
    "DaisyUI",
    "Bootstrap",
    "FastAPI",
    "Next.js",
    "Node.js",
    "React.js",
    "MongoDB",
    "Postman",
    "Express",
    "PyTorch",
    "GitHub",
    "Stream",
    "CI/CD",
    "OAuth",
    "DBMS",
    "HTML",
    "CSS",
    "JWT",
    "OOP",
    "AWS",
    "GCP",
    ".NET",
    "SQL",
    "C++",
    "C#",
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
