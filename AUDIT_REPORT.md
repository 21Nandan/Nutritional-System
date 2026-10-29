# EATGOOD audit report

Date: 2026-10-29 · Baseline: `f1faaf6` (preserved on branch `backup-antigravity-original`) ·
Work branch: `claude/sleepy-franklin-rxra0a`

## Limits of this audit

The work environment could not reach `eatgood26.vercel.app`, Vercel's API, `world.openfoodfacts.org` or
WHO/PubMed pages (the proxy refused the connections), and had no Vercel credentials. **Everything about
the live deployment is unverified.** Everything else below was reproduced locally, with commands and
tests in the repository.

## Findings by severity

### Critical
1. **The catalogue is synthetic but was presented as real and verified.** `scripts/generate_initial_data.py`
   (seed 42) reproduces all 852 products byte for byte: random nutrients, random allergens, random
   barcodes. The records said "Label Scan / Retail Packaging Audit 2026" and "Verified", and the README
   said "852 authentic products". **Fixed:** relabelled as synthetic (nutrient values unchanged), with a
   footer disclaimer, a "Synthetic" badge on each product, an "About the data" page and a dataset
   manifest checked at startup. (A top-of-page banner was added, then removed at the owner's request.)
2. **One visitor's data could reach or harm another.**
   - A new visitor inherited the shared default profile, which anyone could overwrite, allergens included.
   - `GET /api/history` returned everyone's history, and `DELETE /api/history` erased it.
   - Saved items and OCR scan logs were global.

   **Fixed:** the server stores no personal data. The profile lives in the browser and is sent per
   request (goal, diet and allergens only). Tests confirm the old endpoints no longer exist.
3. **Allergen checks ignored the visitor on two paths.** Barcode lookup and the active
   `/api/alternatives` route used the global default profile, so alternatives could include the user's
   allergen. **Fixed:** every path uses the request profile; an invariant test covers catalogue,
   barcode (catalogue, contribution and Open Food Facts), manual/OCR entry, compare, saved items, and
   alternatives for 5 allergens across all 8 categories.

### High
4. **Allergen matching errors.**
   - Declarations matched by exact substring ("Egg" missed Eggs, "almonds" missed Tree Nuts).
   - The "may contain" branch could never run.
   - Custom allergens were never matched.
   - "coconut milk" and "cocoa butter" were flagged as milk.
   - Missing allergen data counted as safe for alternatives.

   **Fixed**, with tests for synonyms, regional names, hidden sources and false positives.
5. **OCR could not work on Vercel** (no Tesseract binary), and "auto-repair" silently changed values
   (3736 g became 37.36 g). **Fixed:** OCR runs in the browser (verified in Chromium, including under
   the production CSP). Impossible values are left empty with a suggestion the user must accept, and
   flagged values need explicit confirmation.
6. **Silent failures.** A missing CSV gave an empty catalogue, SQLite errors fell back to an in-memory
   DB, the ML model silently didn't load, Open Food Facts search errors returned `[]`, and the frontend
   swallowed errors into "No matching products found". **Fixed:** fail-fast loader, `/api/ready`
   returns 503, plain error messages with distinct codes, and separate loading/error/empty states.
7. **Products with no stated measurement basis were graded** against per-100 g thresholds (40
   products). **Fixed:** no grade, with an explanation. Exactly those 40 grades changed and no other.
8. **Open Food Facts client.**
   - Text search used the staging host first.
   - Unknown categories were silently treated as "Snacks" and graded.
   - "Chocolates" matched the beverage keyword "cola".
   - "May contain" traces were never requested.

   **Fixed**, with tests.
9. **The broken emergency entrypoint** (`api/index.py` referenced an out-of-scope `e`) would also have
   published tracebacks and server paths. **Fixed:** import errors now surface in Vercel logs.

### Medium
10. **False or unsupported claims** throughout the README, privacy policy, onboarding and UI: "offline",
    "zero cloud egress", "100% local", "audited", "evidence-based", "AI-powered", an "ML model", test
    counts of 61/36/44. **Rewritten.** The README now lists exactly what leaves the device, and test
    counts come from the CI badge.
11. **Thresholds are unverified.** The "verification dates" had no evidence behind them, and the WHO
    SEARO ISBN was wrong. **Fixed:** ISBN corrected, every entry marked unverified, and full table in
    `docs/THRESHOLDS.md`. No numbers changed.
12. **Catalogue UX.**
    - "Show All" loaded all 852 cards, and pagination didn't know the total.
    - Colour coding used hard-coded 15 g / 600 mg limits that disagreed with the grade.
    - Deep links `/product/IND_PKG_041` were lowercased and returned 404 on reload.
    - First load stripped filter parameters from the URL.
    - Picking a search result kept the previous product's nutrients.

    **All fixed.**
13. **Repository hygiene.**
    - A committed SQLite DB with test data and a local macOS path.
    - Committed `dist/`.
    - Duplicate requirements and `uv.toml`.
    - Dead code: `src/`, the Swift helper, the ML model, image enrichment, 6 unused CSVs.
    - CI on Python 3.9.
    - No linters and no licence.

    **Fixed.** Removed files are kept on the backup branch.

### Low
14. 75 synthetic products have sugars greater than carbohydrates, and the stored report says 13
    serving anomalies where the data shows 12 (`docs/DATA.md`). These products show "Data
    Contradiction" instead of a grade.
15. Product photos: 37 of the original 38 pointed at Open Food Facts' password-protected staging host, so
    none loaded. **Fixed:** 26 now use production links and have names checked against the catalogue; 12
    mismatches were removed and show a placeholder (docs/DATA.md).
    Correctness is unverified.

## What changed (high level)

- Backend split into `routes/`, `products.py`, `profile.py`, `schemas.py` (Pydantic for every body)
  and `errors.py`, with config validated at startup.
- One Python dependency source (`pyproject.toml`) compiled to pinned `requirements*.txt`; Python ≥ 3.12.
- New frontend modules: `api.js`, `storage.js`, `ocr.js`, `format.js`; rewritten
  data page.
- Security headers in `vercel.json` (CSP tested against the running app, Permissions-Policy limiting
  the camera to this site, HSTS); self-hosted fonts and OCR assets; 10 KB logo.
- Tooling: CI (ruff, mypy, pytest with an 82 % coverage floor, bandit, pip-audit, ESLint, build, npm
  audit, Playwright e2e on desktop and mobile, gitleaks), CodeQL, Dependabot, pre-commit, Makefile,
  post-deploy smoke workflow, templates, LICENSE (MIT), SECURITY, CONTRIBUTING, CHANGELOG.

## Verification evidence (local, final run)

| Check | Result |
|---|---|
| pytest | 214 passed; coverage 84 % (allergen engine 97 %, recommender 94 %, routes 81–97 %) |
| ruff / mypy / bandit / pip-audit | clean / clean / no issues / no known vulnerabilities |
| ESLint / Vite build / npm audit | 0 problems / builds with no warnings / 0 vulnerabilities |
| Playwright e2e (desktop + mobile) | 14 passed: catalogue, URL filters, search, empty state, allergen override, compare, saved items, in-browser label OCR (no photo upload) |
| Same flows under the production CSP | no CSP violations, no console errors |
| Dataset regeneration | byte-identical nutrient values; only the provenance label columns changed |

Phase 0 baseline for comparison: 108 tests (105 passed, 1 failed because the Tesseract binary was
missing, 2 skipped), 75 % coverage, 67 ruff F-class errors, no ESLint.

## What remains risky

- **Vercel deployments are failing because of a project setting, not the code.** Every deployment
  since the original commit `f1faaf6` (before this work) failed within seconds. The Root Directory
  appears to be set to `frontend/` (Vercel's PR metadata says "monorepo"). The repository-root build
  succeeds locally with the Vercel CLI, and the assembled function serves the catalogue. Fix: clear
  Root Directory in Vercel project settings and redeploy.
- **Production is untested by me.** The PR's Vercel preview and the smoke workflow must pass before
  merging. The most likely deploy-time risks:
  - Python dependency detection with the new `pyproject.toml` (`requirements.txt` is still present,
    as Vercel expects).
  - `includeFiles` / `excludeFiles` in `vercel.json`.
  - The CSP on Vercel (tested locally only).
- **The data is not real.** Grades and allergen results on catalogue products describe invented values.
- **Thresholds have not been checked against the source documents.**
- Contributions and the Open Food Facts cache are per serverless instance; rate limits are best-effort.
- Phase 6 Layer-1 simplification (before/after for approval), Lighthouse and the responsive audit at
  5 widths were not done in this pass. The mobile e2e project passes, but there was no visual review
  at 320/375/768/1024/1440.

## Decisions and actions only you can take

See the summary at the end of `PROGRESS.md`.
