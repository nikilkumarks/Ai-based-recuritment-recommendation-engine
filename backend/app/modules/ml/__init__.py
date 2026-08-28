"""ML inference module.

Must not import FastAPI. Training code lives in the repo-root `ml/` package and
must not call HTTP APIs. Swap implementations via RANKER_IMPL without changing
the public API contract.
"""
