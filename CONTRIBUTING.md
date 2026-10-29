# Contributing

1. `make setup`, then `make dev`.
2. Create a branch; keep each pull request focused on one change.
3. Before pushing, run `make check` (and `make e2e` for UI changes). CI runs the same checks.
4. Fill in the pull request template.

Rules for this project:

- **Safety first.** An allergen conflict must override the score on every path, and alternatives must
  never include the user's allergens. `backend/tests/test_allergen_safety.py` guards this; extend it
  when you add a path.
- **No silent fallbacks.** Missing values stay missing (never 0). Errors are shown to the user, never
  turned into an empty list.
- **Don't change grading without review.** Thresholds live in `backend/core/standards_registry.py`.
  Changing one needs a source and an entry in `docs/THRESHOLDS.md`.
- **Honest claims.** Don't describe data as verified, audited or authentic unless it is, and don't
  imply endorsement by WHO, FSSAI or others.
- Python dependencies: edit `pyproject.toml`, then `make lock` (updates `uv.lock`, used by Vercel, and `requirements*.txt`, used by CI). Frontend dependencies: `npm install --save-exact`.
- Use plain language in anything a user reads.
