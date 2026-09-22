# ML package (offline)

Training and evaluation for PRJ_385 live here, **not** in FastAPI request handlers.

```bash
python -m ml.train --dataset <dataset_snapshot_id>
python -m ml.evaluate --dataset <dataset_snapshot_id>
```

Recruiter shortlist/reject decisions are behavioral labels and are not ground-truth hiring outcomes.

No trained project model is produced until sufficient real labeled data exists.

If the snapshot has fewer than `MIN_TRAINING_ROWS` real eligible rows (current project data: 3), training prints:

```
Training skipped:
insufficient real labeled data.
Insufficient real labeled data for training experiment.
```

and does not write an artifact.

## Rules

- Do not depend on HTTP requests.
- Do not commit weights or metrics files (`ml/artifacts/` is gitignored).
- Do not report fixture metrics as project accuracy.
- TEST FIXTURE ONLY data in `ml/fixture.py` is for plumbing tests.
- Serving loads an **activated** artifact from `MODEL_ARTIFACT_DIR` with baseline fallback.
- Details: `docs/ML_TRAINING.md`
