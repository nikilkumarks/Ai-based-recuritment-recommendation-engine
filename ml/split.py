"""Group-aware splits. Never put the same job in train and validation of a fold."""

from __future__ import annotations

from sklearn.model_selection import GroupKFold


def group_folds(
    groups: list[str], requested_folds: int
) -> tuple[int, list[tuple[list[int], list[int]]]] | str:
    unique = len(set(groups))
    if unique < 2:
        return "insufficient_unique_jobs_for_groupkfold"
    folds = min(requested_folds, unique)
    if folds < 2:
        return "insufficient_unique_jobs_for_groupkfold"
    splitter = GroupKFold(n_splits=folds)
    X_placeholder = [[0] for _ in groups]
    splits: list[tuple[list[int], list[int]]] = []
    for train_idx, test_idx in splitter.split(X_placeholder, groups=groups):
        train_groups = {groups[i] for i in train_idx}
        test_groups = {groups[i] for i in test_idx}
        if train_groups & test_groups:
            return "job_leakage_in_split"
        splits.append((list(train_idx), list(test_idx)))
    return folds, splits
