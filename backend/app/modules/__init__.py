"""PRJ_385 domain modules.

Routers stay thin and call services. Services contain application logic.
Repositories contain database access. Schemas are API/domain DTOs.

Architectural import bans (enforced in later phases by tests, documented now):

- nlp must not import ml
- ml must not import FastAPI (this package has no router)
- matching must not import ranking
"""
