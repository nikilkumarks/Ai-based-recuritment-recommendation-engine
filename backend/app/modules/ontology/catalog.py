"""Curated CS/IT ontology catalog. V1 is limited and not complete."""

from __future__ import annotations

SEED_VERSION = "seed-0.1"

# (canonical_name, slug, category, description)
SKILLS: tuple[tuple[str, str, str, str], ...] = (
    ("Artificial Intelligence", "artificial-intelligence", "AI/ML", "Parent domain for ML-related skills."),
    ("Machine Learning", "machine-learning", "AI/ML", "Statistical learning methods."),
    ("Deep Learning", "deep-learning", "AI/ML", "Neural-network methods under machine learning."),
    ("Natural Language Processing", "natural-language-processing", "AI/ML", "Language skills."),
    ("Computer Vision", "computer-vision", "AI/ML", "Image and video understanding."),
    ("OpenCV", "opencv", "AI/ML", "Computer vision library."),
    ("TensorFlow", "tensorflow", "AI/ML", "ML framework."),
    ("PyTorch", "pytorch", "AI/ML", "ML framework."),
    ("scikit-learn", "scikit-learn", "AI/ML", "Classical ML library."),
    ("Pandas", "pandas", "AI/ML", "Tabular data library."),
    ("NumPy", "numpy", "AI/ML", "Numerical computing library."),
    ("XGBoost", "xgboost", "AI/ML", "Gradient boosting library."),
    ("Python", "python", "Programming Languages", "General-purpose programming language."),
    ("Java", "java", "Programming Languages", "General-purpose programming language."),
    ("JavaScript", "javascript", "Programming Languages", "Web programming language."),
    ("TypeScript", "typescript", "Programming Languages", "Typed JavaScript."),
    ("C++", "cpp", "Programming Languages", "Systems programming language."),
    ("C#", "csharp", "Programming Languages", "CLI programming language."),
    (".NET", "dotnet", "Programming Languages", "Microsoft application platform."),
    ("Go", "go", "Programming Languages", "Programming language."),
    ("Rust", "rust", "Programming Languages", "Systems programming language."),
    ("SQL", "sql", "Programming Languages", "Query language."),
    ("HTML", "html", "Web Development", "Markup language."),
    ("CSS", "css", "Web Development", "Stylesheet language."),
    ("React", "react", "Web Development", "UI library."),
    ("Next.js", "nextjs", "Web Development", "React framework."),
    ("Node.js", "nodejs", "Web Development", "JavaScript runtime."),
    ("FastAPI", "fastapi", "Web Development", "Python web framework."),
    ("PostgreSQL", "postgresql", "Databases", "Relational database."),
    ("MongoDB", "mongodb", "Databases", "Document database."),
    ("Redis", "redis", "Databases", "In-memory data store."),
    ("Docker", "docker", "Cloud/DevOps", "Container runtime."),
    ("Kubernetes", "kubernetes", "Cloud/DevOps", "Container orchestration."),
    ("CI/CD", "ci-cd", "Cloud/DevOps", "Continuous integration and delivery."),
    ("AWS", "aws", "Cloud/DevOps", "Amazon cloud platform."),
    ("GCP", "gcp", "Cloud/DevOps", "Google cloud platform."),
    ("Git", "git", "Cloud/DevOps", "Version control."),
    ("Linux", "linux", "Cloud/DevOps", "Operating system."),
    ("Apache Spark", "spark", "Data Engineering", "Distributed data processing."),
    ("Apache Kafka", "kafka", "Data Engineering", "Event streaming platform."),
    ("OAuth", "oauth", "Security", "Authorization protocol."),
    ("JWT", "jwt", "Security", "JSON Web Token."),
    ("pytest", "pytest", "Testing", "Python test runner."),
    ("Jest", "jest", "Testing", "JavaScript test runner."),
)

ALIASES: dict[str, tuple[str, ...]] = {
    "artificial-intelligence": ("AI", "A.I.", "artificial intelligence"),
    "machine-learning": ("ML", "machine learning", "machine-learning", "ML algorithms"),
    "deep-learning": ("DL", "deep learning"),
    "natural-language-processing": ("NLP", "natural language processing"),
    "computer-vision": ("CV", "computer vision"),
    "javascript": ("JS", "javascript"),
    "typescript": ("TS", "typescript"),
    "cpp": ("cpp", "cplusplus"),
    "csharp": ("csharp",),
    "dotnet": ("dotnet", "dot net"),
    "nodejs": ("NodeJS", "nodejs"),
    "nextjs": ("nextjs", "NextJS"),
    "ci-cd": ("CICD", "cicd", "continuous integration"),
    "postgresql": ("Postgres", "postgres"),
    "scikit-learn": ("sklearn", "scikit learn"),
    "spark": ("Spark",),
    "kafka": ("Kafka",),
}

# parent_of: source is parent, target is child. Inverse child_of is derived.
PARENT_EDGES: tuple[tuple[str, str], ...] = (
    ("artificial-intelligence", "machine-learning"),
    ("machine-learning", "deep-learning"),
)

RELATED_EDGES: tuple[tuple[str, str], ...] = (
    ("machine-learning", "natural-language-processing"),
    ("machine-learning", "computer-vision"),
    ("computer-vision", "opencv"),
    ("docker", "kubernetes"),
    ("react", "nextjs"),
    ("javascript", "nodejs"),
    ("sql", "postgresql"),
    ("csharp", "dotnet"),
)

SIMILAR_EDGES: tuple[tuple[str, str], ...] = (("tensorflow", "pytorch"),)
