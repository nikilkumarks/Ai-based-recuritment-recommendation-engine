"""Offline evaluation entry point.

Phase 0: no model artifacts and no metrics. Evaluation must compare a trained
model against documented baselines; it must not invent accuracy numbers.
"""

from __future__ import annotations


def main() -> None:
    raise SystemExit(
        "Evaluation is not implemented. There is no trained model or labeled test set."
    )


if __name__ == "__main__":
    main()
