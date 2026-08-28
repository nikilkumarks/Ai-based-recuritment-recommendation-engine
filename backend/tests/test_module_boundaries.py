import ast
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _python_sources(module: str) -> list[Path]:
    return list((BACKEND_ROOT / "app" / "modules" / module).rglob("*.py"))


def _imports_prefix(path: Path, prefix: str) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(prefix):
            return True
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(prefix):
                    return True
    return False


def test_nlp_must_not_import_ml() -> None:
    for path in _python_sources("nlp"):
        assert not _imports_prefix(path, "app.modules.ml")
        assert not _imports_prefix(path, "app.modules.embeddings")


def test_ontology_must_not_import_embeddings() -> None:
    for path in _python_sources("ontology"):
        assert not _imports_prefix(path, "app.modules.embeddings")
        assert not _imports_prefix(path, "app.modules.ml")


def test_embeddings_must_not_import_ml_or_nlp_pipeline() -> None:
    for path in _python_sources("embeddings"):
        assert not _imports_prefix(path, "app.modules.ml")
        assert not _imports_prefix(path, "app.modules.nlp.pipeline")
        assert not _imports_prefix(path, "app.modules.ranking")
        assert not _imports_prefix(path, "app.modules.matching")


def test_matching_must_not_import_ranking_or_ml() -> None:
    for path in _python_sources("matching"):
        assert not _imports_prefix(path, "app.modules.ranking")
        assert not _imports_prefix(path, "app.modules.ml")


def test_ml_module_has_no_fastapi_router() -> None:
    """ML must not import FastAPI; keep inference free of HTTP (ARCHITECTURE.md)."""
    router = BACKEND_ROOT / "app" / "modules" / "ml" / "router.py"
    assert not router.exists()


def test_domain_modules_exist() -> None:
    modules_root = BACKEND_ROOT / "app" / "modules"
    expected = {
        "identity",
        "organizations",
        "documents",
        "nlp",
        "ontology",
        "embeddings",
        "matching",
        "features",
        "ml",
        "ranking",
        "explainability",
        "career",
        "analytics",
        "jobs",
        "candidates",
        "applications",
    }
    present = {path.name for path in modules_root.iterdir() if path.is_dir()}
    assert expected.issubset(present)
