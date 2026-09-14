# Operations and release locking

The API model contract defaults to PaddleOCR-VL 1.6 (0.9B). Set an approved immutable
model revision in `OCR_MODEL_REVISION`; `unlocked-development` is only for local work.

Run `python scripts/check_updates.py --output releases/candidate.json` to collect
candidates. It does not modify dependencies or models. For each candidate: resolve
dependencies against the target Python/CUDA image, perform model-load and inference
smoke tests, run regression tests, then lock the model revision, image digest, and
`pip freeze` output in the release record. A changed model family or output contract
requires explicit adapter and output validation, never a name-only upgrade.
