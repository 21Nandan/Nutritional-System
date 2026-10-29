# EATGOOD — Project Map (Phase 0 baseline, before any changes)

Investigated 2026-10-29 at commit `f1faaf6` on branch `claude/sleepy-franklin-rxra0a`. Nothing in the repository was changed. Every command ran against throwaway copies in the scratchpad, because importing the backend writes to the tracked `data/eatgood_app.db`.

**Network limits in this sandbox:** the environment's network policy blocks `eatgood26.vercel.app` and `world.openfoodfacts.org` (the proxy returned 403 on CONNECT). I also have no access to Vercel logs. So **every statement about the live deployment or Open Food Facts below is unverified.**

---

## 1. What is in the repo (115 tracked files)

| Path | What it does | Used? | Notes |
|---|---|---|---|
| `api/index.py` | Vercel entrypoint. Imports `backend.main:app` and falls back to an "emergency" app if the import fails. | Yes (prod) | **Bug:** the fallback refers to `e` after the `except` block has ended (ruff F821, line 28). In Python 3, `e` is deleted when the block exits, so the fallback crashes with `NameError` on every request. If it did work, it would also show the public the full traceback, `sys.path` and the `/var/task` file listing. |
| `backend/main.py` (1,196 lines) | Every FastAPI route, the Pydantic models, middleware and static file serving. | Yes | `/api/health` is defined **twice** (lines 118 and 227) and `/api/alternatives/{id}` is also defined **twice** (868 and 1068). In each pair the second definition is dead. |
| `backend/config.py` | Reads environment variables. | Yes | `UPLOAD_DIR` is duplicated in `main.py`. |
| `backend/database.py` | SQLite layer. Runs `init_db()` at import time and copies the DB to `/tmp` on Vercel. | Yes | Writes to the tracked DB file. If it cannot open the file it **silently switches to an in-memory DB** (lines 60-64). |
| `backend/core/*.py` (16 modules) | Scoring, standards, allergens, claims, OCR, Open Food Facts client, barcodes, images, search, "assistant", recommender, rate limiter, ML wrapper. | Yes | Scoring logic is reviewed in Phase 5. |
| `backend/core/ml_model.py` + `models/` | RandomForest "personalization matcher" (`eatgood_model.joblib`, 497 KB). | Partly | Its output is attached to product responses as `ml_experimental_insight`. scikit-learn/joblib are **not** in `requirements.txt`, so in production the model silently never loads. Its metadata says it was trained on 1,500 simulated pairs with accuracy 1.0 ("artifact of synthetic labels"). |
| `backend/tests/` (10 files) | pytest suite. | Yes | 108 tests (see §4). |
| `backend/requirements.txt` | Byte-identical to the root `requirements.txt`. | Duplicate | |
| `src/recommend.py`, `src/train_model.py` | Old standalone recommender and model trainer. | **Dead** (nothing imports them) | `train_model.py` is the only reader of `personalization_examples.csv`. |
| `scripts/generate_initial_data.py` | **Generates the whole product dataset with `random.seed(42)`.** | Offline | See §3. This is the most important finding. |
| `scripts/ocr_helper.swift` | macOS Vision OCR helper. | **Dead** (nothing references it) | |
| `data/*.csv` | Catalogue plus "audit" tables. | Partly | `products.csv`, `nutrition_consistency_review.csv` and `flagged_products_inspection.csv` are never read. The last two are byte-identical copies of `nutrition_review.csv` and `serving_size_review.csv`. `products_standardized.csv`, `raw/…csv` and `users.csv` are loaded into memory and never used. |
| `data/eatgood_app.db` | SQLite DB, **committed**. | Yes (shipped to prod as the seed) | Holds developer test data: 143 history rows, 36 scan sessions with raw OCR text, 67 contributions, 4 profiles, and local paths such as `/Users/nandan/3rd sem EL/...`. Older versions in git history hold the profile name "Nandan". |
| `frontend/src/` | React 18 + Vite single-page app: 7 pages, 9 components. | Yes | 25 `fetch` calls with no shared API client. Uses relative `/api/...` URLs (correct for Vercel rewrites). |
| `frontend/dist/` | **Committed build output.** | Local only | Vercel rebuilds it. I confirmed it matches a fresh build (same hashes). |
| `frontend/.vercelignore`, root `.vercelignore` | Exclude tests, venv and uploads. | Yes | Neither excludes `data/` or `models/`. |
| `vercel.json` | Build command, `includeFiles: "{backend/**,data/**,models/**}"`, rewrites. | Yes | The build command contains an `unset npm_config_cache_dir` workaround. |
| `pyproject.toml` + `uv.toml` | Both contain only `link-mode = "copy"`. | Duplicate | `pyproject.toml` has no `[project]` table and no `requires-python`. |
| `package.json` (root) | Wraps the build and `uvicorn`. | Partly | |
| `run.sh`, `start.command` | Local launchers. | Local | `run.sh` installs packages that are not pinned, and that list differs from `requirements.txt`. |
| `.github/workflows/ci.yml` | pytest on **Python 3.9** plus the frontend build. | Yes | Triggers only on `main`/`master`. |
| `README.md`, `EATGOOD_ARCHITECTURE_AND_SPECIFICATION.{md,html}`, `AUDIT_REPORT.md` | Docs. The spec exists in both `.md` and `.html`. | | `AUDIT_REPORT.md` comes from the previous AI session. Several of its claims are stale or wrong (see §6). |

## 2. How the app works (plain language)

There is one FastAPI process. On Vercel it runs as a serverless function behind `/api/*`, and the React build is served as static files. Locally, `uvicorn` serves both.

**On startup (at import time):** `data_loader` reads 7 CSVs with pandas, seeds 38 image records into SQLite and merges them into the catalogue. `database.init_db()` creates the tables. On Vercel the DB is first copied to `/tmp`. If any CSV is missing, the loader uses an **empty table without raising an error**.

- **Catalogue:** `ProductCatalogue.jsx` calls `GET /api/products/categories` and `GET /api/products?limit=1000` (the page size defaults to "All"). The data is filtered in memory with pandas. A query of two or more words is handled by a keyword "semantic" parser.
- **Product details / assessment:** `GET /api/products/{id}` → `run_full_product_assessment` (Layer 1 general grade, Layer 2 personal fit, Layer 3 details) + allergen check + ML "insight". The result is also written to `analysis_history`.
- **Barcode:** the browser decodes the barcode with ZXing → `GET /api/products/barcode/{code}`. The order is: local catalogue → user contributions → SQLite cache → Open Food Facts v3 (httpx with the certifi bundle). Errors come back as `OFF_*` codes.
- **OCR:** upload → `POST /api/analyze/ocr`. Uses Google Cloud Vision if `VISION_API_KEY` is set, otherwise a local Tesseract binary. A regex parser then extracts the nutrients. The image is saved to `data/uploads` (or `/tmp`), and the raw text is stored in `scan_sessions`.
- **Profile:** the browser creates `eatgood_client_id` in localStorage and sends it as `?user_id=`. Profiles are keyed by that ID. **There is no authentication.**

## 3. The dataset is synthetic (verified)

Running `scripts/generate_initial_data.py` on a clean copy reproduces `raw/packaged_foods_india.csv`, `products.csv`, `products_cleaned.csv`, `products_standardized.csv`, `users.csv`, `personalization_examples.csv` and `nutrition_review.csv` **byte for byte**.

- Every nutrient value is `random.uniform(...)` within a range per category. Energy is computed with the Atwater formula, and then exactly 78 anomalies and 13 serving flags are injected on purpose ("calibrated to strictly match the project development history").
- **Allergens are `random.choice(ALLERGEN_OPTIONS)`.** For example, Haldiram's Navratan Mix is listed with "Milk, Tree Nuts", while its "(Variant 2)" is listed with "Gluten, Milk, Soy". The ingredient text is one of 29 strings chosen at random.
- Barcodes are `"890" + random 10 digits`. Only 70 of 852 have a valid EAN-13 check digit. Some may belong to real, unrelated products.
- 566 of 852 rows are "(Variant N)" duplicates of the same brand and product.
- Every row says `data_source = "Label Scan / Retail Packaging Audit 2026"` and 726 rows say "Verified". **This provenance is false.** The README calls the data "852 authentic Indian packaged food products".
- Images: 38 of 852 products have an image. All 38 are hotlinked Open Food Facts URLs (37 on `images.openfoodfacts.net`, a staging host, and 1 on `.org`). 14 are labelled `matching_method: exact_barcode`, but **none** of the 38 URL barcodes matches the product's barcode in the dataset. Whether each image shows the right product is unverified, because Open Food Facts is blocked here.

For an app whose purpose is trustworthy allergen and nutrition guidance, this is the root problem. Every grade, allergen warning and alternative is computed on invented numbers.

## 4. Local baseline (evidence)

| Check | Result |
|---|---|
| Backend import with **only** `requirements.txt` (what Vercel installs), Python 3.13 | OK in 0.91 s, 852 rows, `ml loaded False` |
| `/api/health`, `/api/ready`, `/api/products`, `/api/products/categories`, `/api/products/search?q=maggi` | All 200 locally. 8 categories, total 852. |
| `/api/ocr/status` | `available: false` (no Tesseract, no key) |
| `/api/products/barcode/8901058000290` | 502 `OFF_NETWORK_ERROR`, with a plain message (Open Food Facts blocked by this sandbox, **not** a TLS error) |
| pytest (all deps, Tesseract absent) | **108 collected: 105 passed, 1 failed, 2 skipped.** The failure is `test_ocr_engine_status`, which asserts that Tesseract is installed. Coverage is 75% overall: scoring 72%, claims 63%, OCR 66%, `main.py` 69%. |
| Frontend `npm ci && npm run build` (Node 22, Vite 6.4.5) | Builds cleanly with no warnings. Largest chunk is zxing at 454 KB (117 KB gzip). `npm audit`: 0 vulnerabilities. |
| Lint | No linter is configured for either language. `ruff --select F`: 58 unused imports, 6 unused variables, 3 redefinitions, **1 undefined name** (`api/index.py`). No ESLint. |
| Test-count claims in the README | 61, 36 and 44 in three places. The real number is **108**. |

## 5. Features and their status

| Feature | Local | Live |
|---|---|---|
| Catalogue list, categories, filters | Working | Unverified (reported empty) |
| Keyword and "semantic" search | Working | Unverified |
| Product assessment (3 layers) | Working, but on synthetic data | Unverified |
| Allergen check | Code runs, but **input allergen data is random** | Unverified |
| Healthier alternatives | Working (synthetic data) | Unverified |
| Compare | Working (by code path; I did not drive the UI) | Unverified |
| Barcode → catalogue | Working, but only matches the fake barcodes | Unverified |
| Barcode → Open Food Facts | Unverified (blocked here). The certifi fix is present in `openfoodfacts.py`. | Unverified |
| OCR (Tesseract) | Broken without the binary | Broken by design on Vercel, which has no binary |
| OCR (Cloud Vision) | Unverified (needs a key) | Unverified, and whether `VISION_API_KEY` is set on Vercel is unknown |
| Profile per device | Working, **but see the security issues below** | Unverified, and data is ephemeral on serverless (by code reading) |
| Saved products | Working, but **global and shared by all visitors** | Unverified |
| History, recent scans | Working, but **cross-user leak** | Unverified |
| User contributions | Working, shown without moderation | Unverified |
| Data audit page | Working, shows the injected 78/13 numbers | Unverified |
| ML "insight" | Loads locally only if sklearn is installed | Never loads (no sklearn) |

## 6. Security and privacy findings (reproduced locally on a scratch copy)

- `POST /api/profile` without a `user_id` overwrites the shared `USR_DEFAULT` profile. Any **new visitor** whose ID has no row yet is then given that profile (`get_active_profile` falls back to it). I set the name to "Attacker" and a new `user_id=brand_new_visitor` received it. That means a stranger's allergen settings can be applied to someone else.
- `GET /api/history` without a `user_id` returns every user's history. **`DELETE /api/history` without a `user_id` deletes every user's history** (I confirmed this returns 200 and the table is then empty).
- `GET /api/saved` and `/api/saved/check` take no user at all: there is one shared list for everyone.
- `GET /api/scans/recent` returns every user's raw OCR text and server file paths.
- `user_id` is a guessable, unauthenticated query parameter.
- Path traversal through the SPA catch-all was tested and is **not** exploitable (it returns `index.html`).
- **Secrets:** no API keys, tokens or private keys anywhere in git history. No `.env`, venv or `node_modules` was ever committed. The DB file **was** committed (11 versions in history, plus a duplicate `frontend/data/` copy that has since been deleted). Those versions hold test data, the name "Nandan" and local macOS paths. No uploaded images were ever committed.

## 7. Prioritized issue list

**P0: trust and safety**
1. The catalogue is synthetic but presented as real, audited and verified, with random allergens. This matters more than any hosting fix.
2. Profile fallback and cross-user leaks: a new visitor can inherit another person's profile (including allergens), and one unauthenticated call wipes all history.
3. Live catalogue reported empty. The root cause is **unverified**: the previous `AUDIT_REPORT.md` recorded 500s *before* commit `f1faaf6` changed `includeFiles`, and I cannot reach the site or logs to check the current state.
4. The `api/index.py` fallback is broken (`NameError`), so import errors on Vercel cannot be diagnosed, and if it worked it would leak tracebacks publicly.

**P1: production correctness**
5. OCR cannot work on Vercel without `VISION_API_KEY`. Whether the key is set is unknown.
6. SQLite in `/tmp` on serverless: data is lost per instance (by code reading; not tested on Vercel).
7. Silent fallbacks: missing CSV → empty catalogue, DB failure → in-memory DB, ML missing → silently skipped, category fetch errors swallowed in the UI.
8. A committed DB with test data and personal paths is shipped as the production seed.
9. Images: 38 of 852 have one, all hotlinked from a staging host, and the "exact_barcode" labels are false.

**P2: build, docs and hygiene**
10. Duplicate routes, duplicate requirements, `uv.toml` vs `[tool.uv]`, no lockfile for Python, CI on EOL Python 3.9, unpinned `run.sh`.
11. Dead code: `src/`, `ocr_helper.swift`, 3 unused CSVs and 3 loaded-but-unused DataFrames, a duplicate spec HTML, committed `dist/`.
12. False claims in README and UI: "authentic", "audited", "evidence-based", "offline, zero cloud egress", "AI for Social Good". Test counts 61/36/44 vs a real 108. No LICENSE file.
13. No linters, 75% coverage, and a test that requires Tesseract to be installed.

---

## Decisions needed from you

1. **Dataset (blocks Phases 4 and 5):** the catalogue is randomly generated. Options: (a) label it clearly as *demo data* everywhere and keep it for now; (b) replace it with real data (for example, an Open Food Facts India export under ODbL, which is real but incomplete); (c) both, with demo labelling now and real data later. Which do you want? I recommend (c).
2. **Live site access:** may I get network access to `eatgood26.vercel.app` (and `world.openfoodfacts.org`)? You can add them under *Allowed domains* in this cloud environment's network settings. If you prefer, you can paste the output of `curl -i https://eatgood26.vercel.app/api/ready` and the Vercel function logs yourself.
3. **Is `VISION_API_KEY` set in your Vercel project?** Yes or no is enough, and please never paste the key itself.
4. **Where should PROJECT_MAP.md live?** It is in the scratchpad for now because you said not to modify files. Should I put it in the repo root or in `/docs` when we start editing?
5. **Approve starting Phase 1**, with the cross-user profile/history leak (issue 2) added to the P0 scope?
