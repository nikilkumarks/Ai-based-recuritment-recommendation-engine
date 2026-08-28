"""HTTP routes for this module. Not mounted in Phase 0.

Keep this router thin: validate input, call the service, return schemas.
No ranking weights, NLP, or ML inference belong here.
"""

from fastapi import APIRouter

router = APIRouter()
