"""Offline training entry point.

Phase 0: no dataset, no labels, no training. Do not call HTTP APIs from this
module. When training is implemented, it must read feature snapshots and write
artifacts under ml/artifacts/.
"""

from __future__ import annotations


def main() -> None:
    raise SystemExit(
        "Training is not implemented. Finalize docs/ML.md (target, labels, split) "
        "before adding a trainer."
    )


if __name__ == "__main__":
    main()
