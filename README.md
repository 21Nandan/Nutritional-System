# EATGOOD: AI-Powered Personalized Food Safety and Nutrition Assessment

> **Evidence-Based Food Safety & Nutrition Intelligence Platform**  
> **Theme:** AI for Social Good  
> **Primary Objective:** Convert complex packaged-food labels into simple, transparent, evidence-based, and personalized assessments using international standards (WHO, FSSAI, Codex) and machine learning.

---

## 1. Quick Start & Execution

The application is completely self-contained, offline-capable, and runs entirely locally.

### Prerequisites
- **Python 3.9+**
- **Node.js 18+** & npm
- **Tesseract 5+** (Homebrew on macOS: `brew install tesseract`)

### Start the Application (Single Command)
```bash
./run.sh
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your web browser.

### Alternatively, Run Backend & Frontend in Development Mode:
**Terminal 1 — Backend (FastAPI):**
```bash
source backend/venv/bin/activate
PYTHONPATH=. uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend (Vite React):**
```bash
cd frontend
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser.

### Run Automated Unit, OCR, Barcode, Security & Claim Auditor Tests:
```bash
PYTHONPATH=. backend/venv/bin/pytest backend/tests/ -v
```
*(All 61 automated unit, OCR, barcode format, Open Food Facts, security, rate limiting, claim taxonomy, and contribution tests pass).*

---

## 2. Technology Stack

| Layer | Component | Version / Technology | Key Role |
|---|---|---|---|
| **Frontend** | React & Vite | React 18, Vite 6, Lucide React | Single-page responsive UI, camera upload, editable confirmation screen |
| **Styling** | CSS3 & Design System | Vanilla CSS with CSS Variables | Editorial nature theme (`#143828`), mobile-first responsive grid system |
| **Backend** | Python & FastAPI | Python 3.9+, FastAPI, Uvicorn | RESTful API, validation, standards evaluation, provenance tracking |
| **Data Engine** | Pandas & NumPy | Pandas 2.2+, NumPy 2.0+ | Dataset normalization, calorie consistency audits, Atwater cross-checks |
| **Computer Vision** | OpenCV & Pillow | OpenCV 5.0+, Pillow 11.3+ | EXIF orientation, CLAHE contrast enhancement, bilateral filtering, resizing |
| **OCR Engine** | Tesseract 5 & pytesseract | Tesseract 5.5.3, pytesseract 0.3.13 | Local offline optical character recognition, bounding box and confidence data |
| **Database** | SQLite 3 | Embedded SQLite (`data/eatgood_app.db`) | Local user profiles, scan session logs, analysis history, saved products |
| **Testing** | pytest & HTTPX | pytest 8.4+, HTTPX 0.28+ | Automated core logic, OCR regression fixtures, and API upload integration tests |

---

## 3. Database Architecture Decision: SQLite vs. MongoDB

An architectural evaluation was conducted between SQLite and MongoDB for local persistence:

### Architectural Analysis:
1. **Local-First & Offline Mandate:** EATGOOD is strictly designed as a zero-cloud-egress, local-first personal health tool. It does not transmit food-label photos, diet preferences, or scan history to third parties.
2. **Operational Overhead:** MongoDB requires running a separate background daemon (`mongod`), managing disk socket locks, memory caches, and external service lifecycles. If `mongod` fails to launch or is not installed, the application breaks.
3. **Storage Efficiency & Performance:** SQLite is embedded directly into the Python process (`sqlite3` built into standard library). It stores profiles, saved products, and full scan history in a compact, portable 40KB file (`data/eatgood_app.db`) with instant sub-millisecond query latency and zero configuration.
4. **Structured Provenance:** Scan sessions, raw OCR text, structured JSON nutrition snapshots, and user profiles are cleanly structured in SQLite with transactional integrity.

### Engineering Decision:
**Retain and enhance SQLite.** SQLite perfectly satisfies all project requirements without introducing unnecessary infrastructure complexity. 
A dedicated `scan_sessions` table was added to record every local OCR upload:
- `scan_id`: Unique identifier (`scn_{uuid}`)
- `filename`: Uploaded file name
- `image_path`: Path to stored local image
- `ocr_engine`: OCR engine version string (`Tesseract 5.5.3 (Local)`)
- `raw_text`: Complete unedited OCR string
- `status`: Session extraction status (`success`, `partial`, `no_text_found`)
- `extracted_data`: JSON snapshot of extracted nutrition metrics
- `confidence`: Average word confidence score (0.0 to 1.0)
- `created_at`: ISO 8601 timestamp

---

## 4. OCR Bug Investigation & Root Cause Elimination

### Root Cause Analysis:
Previously, different uploaded food label photographs produced identical or nearly identical outputs. Through step-by-step code inspection and trace analysis, four root causes were identified:
1. **Silent Fallback Mock in `backend/core/ocr_service.py:38-43`:** When OCR binary execution failed, timed out, or threw an exception, the exception handler caught the error and silently returned a hardcoded mock nutrition dictionary (`Energy: 450 kcal, Carbs: 62.0g, Sugars: 14.5g, Protein: 7.8g, Fat: 18.2g, Sat Fat: 8.5g, Sodium: 420mg`).
2. **Subprocess Timeout on Camera Images:** High-resolution smartphone photos (e.g. 6.2MB iPhone photos) exceeded a 10-second timeout on un-preprocessed images, repeatedly triggering the silent mock fallback.
3. **Hardcoded `"status": "success"` in `backend/main.py:231`:** The backend unconditionally returned `"status": "success"` even when the OCR engine returned `status: "fallback"`.
4. **Non-Unique Reused File Paths:** Images were saved to a static path `scan_{filename}` without unique session IDs, causing overwrites and stale state.

### Upgraded Multi-Stage OCR Architecture:
- **Stage 1: Safe Upload & Session Isolation:** Each upload receives a unique ID (`scn_{uuid}`) and is saved with sanitized filenames. Supported formats: PNG, JPEG, WebP. Corrupt or unreadable files return HTTP 400.
- **Stage 2: OpenCV Preprocessing Pipeline:**
  - EXIF rotation correction via `ImageOps.exif_transpose` (handles portrait/landscape phone orientations).
  - Dimension normalization: Downsamples huge phone photos (>2000px) to prevent timeouts while upscaling small screenshot text (<650px) using cubic interpolation.
  - Conversion to grayscale and Bilateral Filtering (`cv2.bilateralFilter`) to remove packaging glare while preserving sharp character contours.
  - Contrast-Limited Adaptive Histogram Equalization (`CLAHE`) to enhance low-contrast packaging print.
- **Stage 3: Tesseract 5 Multi-Pass Execution:**
  - Runs Tesseract 5 with `--oem 3 --psm 6` (uniform tabular layout) followed by `--psm 3` if text is sparse.
  - Computes word-level extraction confidence via `image_to_data`.
  - **Zero Silent Fallbacks:** If no text is detected, returns `status: "no_text_found"` with empty values and explicit user instructions. NEVER mock data.
- **Stage 4: Heuristic Nutrition Parser & Scientific Audits:**
  - Robust regex supporting both inline (`Energy: 602 kcal`) and tabular layouts.
  - OCR artifact repairs: Auto-repairs missing decimal points (e.g. `3736g` -> `37.36g`) when macros exceed physical boundaries, tagging the field as `needs_review` with an explanatory note. Corrects `Og` to `0g` and `<01` to `0.1`.
  - Cross-checks: Atwater caloric discrepancy ($4C + 4P + 9F \approx \text{kcal}$), Saturated Fat $\le$ Total Fat, and Sugars $\le$ Total Carbs.
- **Stage 5: Confirmation Interface:** The frontend displays per-field status tags (Green `✓ Extracted`, Yellow `⚠️ Needs Review`, Gray `Manual`), raw OCR text accordion, and requires user review before generating the 3-layer assessment.

---

## 5. Mobile Responsiveness & Touch Optimization

The frontend has been verified across viewports (320px, 375px, 600px, 768px, 1024px, 1440px):
1. **Responsive Navigation:** Added a mobile hamburger toggle button (<860px) that expands into a touch-friendly drawer menu with 44px+ touch targets, resolving the issue where links previously disappeared on small screens.
2. **Camera Integration:** The Label Scanner provides dual inputs: a standard file picker and a direct camera capture trigger (`accept="image/*" capture="environment"`) for smartphones.
3. **Horizontal Overflow Elimination:** Added `overflow-x: hidden` on root containers and wrapped data tables (calculation ledger, product comparison matrix) in touch-scrolling containers (`-webkit-overflow-scrolling: touch`) with min-widths so columns remain readable without clipping.
4. **Responsive Cards:** The 2-column assessment grid wraps automatically into stacked cards on narrow mobile viewports (`repeat(auto-fit, minmax(280px, 1fr))`).
5. **iOS Zoom Prevention:** Set input font sizes to 16px on small screens to prevent unwanted viewport zooming when focusing text inputs on iOS.

---

## 6. Project Architecture & 3-Layer Assessment Engine

```
                  ┌──────────────────────────────────────────────┐
                  │          Product Input / OCR Scan            │
                  └──────────────────────┬───────────────────────┘
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │       LAYER 1: General Nutrition Grade       │
                  │   WHO SEARO & FSSAI INR Reference Criteria   │
                  │ (Snacks, Breakfast Cereals, Beverages)       │
                  └──────────────────────┬───────────────────────┘
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │    LAYER 2: Personalized Goal Suitability    │
                  │  1–100 Score Tailored to User Objectives     │
                  │ (Reduce Sugar, Reduce Sodium, Protein, etc.) │
                  └──────────────────────┬───────────────────────┘
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │   LAYER 3: Allergens & Food Safety Warnings  │
                  │ Strict Safety Exclusions & Additive Context  │
                  │ (High Score NEVER overrides Allergen Alert!) │
                  └──────────────────────┬───────────────────────┘
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │    Healthier Same-Category Alternatives      │
                  │   Comparative Deltas (-45% Sugar, +3g Fibre) │
                  └──────────────────────────────────────────────┘
```

### Layer 1: General Nutritional Assessment
- **Calibrated Scope:** Snacks, Breakfast Cereals, Packaged Beverages.
- **Reference Standards:** WHO South-East Asia Regional Nutrient Profile Model (2017), WHO Sugar Guidance (2020), FSSAI Draft Indian Nutrition Rating (INR 2022), and Codex Alimentarius (CAC/GL 23-1997).
- **Uncalibrated Scope:** Categories outside the calibrated benchmarks (e.g. Chocolates, Condiments, Dairy) display raw nutrition facts with an explicit calibration disclaimer rather than an unsupported grade.
- **Missing Data Rule:** Products missing baseline nutrients (Sugars, Sodium, Saturated Fat) receive *"Insufficient Data for Reliable Assessment"* rather than a fabricated letter grade.

### Layer 2: Personalized Suitability (1 to 100 Scale)
- Calibrated 1 to 100 score where 1 represents least suitable and 100 represents most suitable for the active profile:
  - **Reduce Sugar:** Rewards total sugars $\le 3\text{g}/100\text{g}$, penalizes $>10\text{g}$ and $>20\text{g}$.
  - **Reduce Sodium:** Rewards sodium $\le 140\text{mg}$, penalizes $>400\text{mg}$ and $>900\text{mg}$.
  - **Increase Fibre:** Rewards verified dietary fibre $\ge 3\text{g}$ and $\ge 6\text{g}/100\text{g}$.
  - **Increase Protein:** Rewards protein $\ge 7\text{g}$ and $\ge 12\text{g}/100\text{g}$.
  - **Balanced Choices:** Multi-nutrient balance incorporating healthy macro ratios.
- Includes a transparent mathematical calculation ledger detailing each baseline, bonus, and penalty point.

### Layer 3: Ingredient, Allergen, and Additive Assessment
- Evaluates 10 major allergens: Milk, Soy, Gluten (Wheat), Peanuts, Tree Nuts, Eggs, Fish, Crustaceans, Sesame, Sulphites.
- **Critical Conflict Override:** If a product contains an allergen listed in the user's restrictions, the suitability score is **overridden to 0** with a prominent safety banner.
- **Additive Registry:** Cross-references INS codes (e.g. INS 621 MSG, INS 102 Tartrazine, INS 211 Sodium Benzoate) against authoritative Codex/FSSAI regulatory context without unjustified toxicology panic.

---

## 7. Machine Learning Model Disclosure

- **Artifact:** `models/eatgood_model.joblib` & `models/model_metadata.json`
- **Training Script:** `src/train_model.py`
- **Training Set:** 1,500 simulated user-product recommendation pairs across 100 simulated user profiles (`data/personalization_examples.csv`).
- **Model Transparency Note:** The reported 100% test accuracy is an artifact of evaluation on synthetically generated rule-based labels. It is **NOT** evidence of real-world clinical validity.
- **Integration Policy:** The ML model serves as an experimental architectural component demonstrating ML service integration alongside deterministic nutrition rules. Deterministic nutrition rules serve as the primary ground truth.

---

## 8. Dataset Governance & Calibrated Anomaly Counts

The dataset comprises **852 authentic Indian packaged food products** across 8 categories:

| Data Layer | Path | Description |
|---|---|---|
| **Raw Dataset** | `data/raw/packaged_foods_india.csv` | Preserves original source packaging declarations across 25 columns. |
| **Cleaned Dataset** | `data/products_cleaned.csv` | Type-sanitized dataset with data quality anomaly flags. |
| **Standardized Dataset** | `data/products_standardized.csv` | Normalized per-100g/ml metrics. Records with ambiguous measurement bases remain blank (never 0). |
| **Quality Audit Report** | `data/data_quality_report.csv` | Overall statistical audit of dataset completeness. |
| **Atwater Calorie Review** | `data/nutrition_review.csv` | Exactly **78 products** flagged where $\lvert\text{Reported Energy} - (4C + 4P + 9F)\rvert > 50\text{ kcal}$ or $>25\%$. |
| **Macro > Serving Review** | `data/serving_size_review.csv` | Exactly **13 records** flagged where $C + P + F > \text{Stated Serving Size}$. |
| **Users Database** | `data/users.csv` | 100 simulated user profiles with diverse dietary goals and restrictions. |

---

## 9. Automated Test Verification

Run all test suites:
```bash
PYTHONPATH=. backend/venv/bin/pytest backend/tests/ -v
```

### Verified Test Cases (36/36 Passing):
1. `test_gs1_check_digit_calculation`: Verifies GS1 Modulo-10 check digit math across EAN-13, EAN-8, UPC-A.
2. `test_leading_zeros_preserved`: Asserts leading zeros are strictly preserved as strings (`0012345678905`).
3. `test_barcode_format_detection`: Asserts format classification for EAN-13, EAN-8, UPC-A, and non-numeric validation.
4. `test_normalize_upc_to_ean13`: Asserts 12-digit UPC-A to 13-digit EAN-13 conversion by prepending 0.
5. `test_lookup_local_product_by_barcode`: Asserts Layer 1 local catalogue hit returns full product, assessment, and alternatives.
6. `test_lookup_openfoodfacts_mocked_hit`: Asserts Layer 2 Open Food Facts v3 integration parses external nutrition and ODbL attribution.
7. `test_lookup_openfoodfacts_not_found`: Asserts unlisted barcode returns structured 404 response.
8. `test_user_product_contribution_and_retrieval`: Asserts product contribution persists to SQLite and enables layered lookup as "User Submitted (Unverified)".
9. `test_duplicate_contribution_rejected_if_in_local_db`: Asserts duplicate barcode contributions return HTTP 409 Conflict.
10. `test_healthier_alternatives_endpoint`: Asserts `/api/alternatives/{product_id}` returns goal-aligned substitutes with comparative advantages.
11. `test_invalid_check_digit_flagged_in_strict_mode`: Asserts invalid check digits are caught in strict validation mode.
12. `test_empty_and_whitespace_barcode_handling`: Asserts empty or whitespace barcode strings are cleanly rejected.
13. `test_openfoodfacts_barcode_mismatch_rejected`: Asserts external API returning a code different from the requested barcode is rejected.
14. `test_openfoodfacts_rate_limit_handling`: Asserts 429 rate limit responses produce friendly user warnings without server crash.
15. `test_openfoodfacts_timeout_handling`: Asserts network timeouts (8.0s limit) are safely caught and return structured 502.
16. `test_off_normalization_extracts_proteins_and_additives`: Asserts `proteins_100g`, `additives_tags` (`INS 150d`), and `allergens_tags` are normalized accurately.
17. `test_products_search_endpoint_with_query_and_q`: Asserts `GET /api/products/search?q={query}` returns filtered results.
18. `test_post_products_alias_endpoint`: Asserts `POST /api/products` creates user product contributions with unverified status.
19. `test_direct_barcode_lookup_on_product_endpoint`: Asserts `GET /api/products/{barcode}` resolves numeric barcodes.
20. `test_data_loader_integrity`: Verifies multi-tier CSV loading and fallback handling.
21. `test_layer1_calibrated_vs_uncalibrated`: Asserts calibrated categories receive grades and uncalibrated receive disclaimers.
22. `test_missing_data_refusal`: Asserts products missing core metrics receive refusal notices rather than fake grades.
23. `test_allergen_critical_conflict`: Asserts allergen conflicts override scores to 0.
24. `test_goal_personalization_delta`: Asserts goal-specific scoring delta between low-sugar and high-sugar profiles.
25. `test_misleading_claims_evaluation`: Asserts claims like "low fat" are audited against actual nutrition values.
26. `test_incomplete_data_no_score`: Asserts manual entries with missing metrics suppress scores and request complete input.
27. `test_score_calculation_breakdown_and_scale`: Asserts 1–100 scale math ledger steps and point tallies.
28. `test_product_catalogue_nutritional_filters`: Asserts healthy level filters (sugar <= 10g, sodium <= 400mg).
29. `test_ocr_engine_status`: Asserts local Tesseract 5 is accessible and reports valid version.
30. `test_image_preprocessing`: Asserts OpenCV preprocessing handles EXIF rotation and dimensions.
31. `test_distinct_images_produce_distinct_text`: Asserts different uploads produce genuinely distinct text and calorie metrics.
32. `test_no_silent_fallback_on_blank_image`: Asserts blank images return `no_text_found`, never 450 kcal mock data.
33. `test_macro_glitch_repair_and_field_status`: Asserts OCR decimal glitches (e.g. 3736g) are repaired and flagged `needs_review`.
34. `test_atwater_calorie_crosscheck`: Asserts Atwater discrepancy detection.
35. `test_sub_nutrient_consistency_checks`: Asserts impossible values (Sat Fat > Fat) trigger inconsistency flags.
36. `test_api_analyze_ocr_integration`: Asserts full HTTP file-upload OCR route and SQLite scan logging.

---

## 10. Barcode Scanner & Open Food Facts v3 Integration

### How Barcode Scanning Works:
1. **Camera Scanner (`BarcodeCameraScanner.jsx`):**
   - Built with `@zxing/browser` and `@zxing/library` configured specifically for retail 1D barcodes: `EAN-13`, `EAN-8`, `UPC-A`, `UPC-E`.
   - Explicit user controls: **Start Scanning**, **Stop Scanning / Pause**, **Flip Camera**, **Flashlight / Torch** (on supported mobile devices), and **Enter Barcode Manually**.
   - Rear camera preference (`facingMode: { ideal: "environment" }`).
   - Clean lifecycle management: stops all video tracks and decoders on unmount, page switch, or user cancellation to avoid background battery or resource drain.
   - Throttling & debounce: locks scanner for 2.5s upon detection and validates numeric length (8–14 digits) to prevent duplicate API requests.
2. **Layered Barcode Discovery (`GET /api/products/barcode/{barcode}`):**
   - **Step 1 — Format & Check-Digit Validation:** Validates length and GS1 modulo-10 check digit while strictly preserving string leading zeros.
   - **Step 2 — Local Catalogue Check:** Searches the 852-item Indian retail packaged food database. Supports 12-digit UPC $\leftrightarrow$ 13-digit EAN normalization.
   - **Step 3 — User Contributions Check:** Queries SQLite `user_contributions` table for community-added products.
   - **Step 4 — SQLite Cache Check:** Searches `external_products_cache` (7-day TTL) for recently fetched community products.
   - **Step 5 — Live Open Food Facts API v3:** Queries `https://world.openfoodfacts.org/api/v3/product/{barcode}.json` with targeted field selection and compliant `User-Agent: EATGOOD-NutritionScanner/1.0`.
   - **Step 6 — Exact Product Identity Check:** Asserts that the returned code matches the requested barcode. Mismatched codes are rejected.
   - **Step 7 — Comprehensive Normalization:** Standardizes macronutrients (including protein, carbohydrates, sugars, added sugars, total fat, saturated fat, trans fat, fibre, sodium/salt), maps European E-numbers to statutory INS additives, extracts declared allergens, and separates third-party indicators (Nutri-Score, NOVA) from EATGOOD's calculated scores.
   - **Step 8 — Multi-Layer Assessment:** Feeds the normalized product to EATGOOD's Layer 1 (general nutritional grade), Layer 2 (personalized 1–100 suitability ledger), and Layer 3 (allergen/additive audit).
3. **Product Search & Manual Fallback:**
   - If a barcode is unlisted or scanning is unavailable, users can:
     - Enter the barcode digits manually with instant validation.
     - Search the catalogue by product name or brand via `GET /api/products/search?q={query}`.
     - Switch to package nutrition photo OCR upload (`/api/analyze/ocr`).
     - Submit an unlisted product for local review via `POST /api/products`.
4. **Data Attribution & Licensing:**
   - External product data retrieved from Open Food Facts is licensed under the Open Database License (ODbL). EATGOOD clearly cites Open Food Facts and shows the exact retrieval timestamp and community provenance badge.

---

## 11. Database Setup & Indexing

The project uses embedded SQLite (`data/eatgood_app.db`), requiring zero background daemons.
- **`user_profile`**: Stores personalized health goals, dietary preferences, and allergen exclusions.
- **`analysis_history`**: Tracks user scan and assessment logs with local timestamps.
- **`saved_products`**: Local favorites library.
- **`scan_sessions`**: Complete provenance records for OCR uploads (raw text, bounding box confidence, extracted fields).
- **`external_products_cache`**: Caches Open Food Facts lookups with indexed `barcode PRIMARY KEY` and expiration timestamps.
- **`user_contributions`**: Stores community submissions with an index on `barcode` (`idx_user_contrib_barcode`).

To re-initialize or migrate the database:
```bash
PYTHONPATH=. backend/venv/bin/python -c "from backend.database import init_db; init_db(); print('Database initialized successfully!')"
```

---

## 12. Deployment & Troubleshooting

### Local Development vs. Production:
- **Local Dev Server:**
  - Backend runs on `http://127.0.0.1:8000` via Uvicorn.
  - Frontend runs on `http://localhost:5173` via Vite, configured to proxy `/api` calls to `http://127.0.0.1:8000`.
- **Production Serverless Deployment (Vercel):**
  - `vercel.json` routes `/api/(.*)` to `api/index.py` (FastAPI ASGI handler) and static assets to `frontend/dist`.
  - In serverless environments, SQLite safely operates in `/tmp/eatgood_data/eatgood_app.db` with full read/write support.

### Troubleshooting:
- **Camera Access / Permission Denied:**
  - Modern browsers require a secure context (**HTTPS** or **localhost/127.0.0.1**) for `navigator.mediaDevices.getUserMedia`.
  - If testing from a smartphone on the local network, use an HTTPS tunnel (e.g. `mkcert` or ngrok) or USB port forwarding (`chrome://inspect`).
  - Ensure the browser tab has camera permission granted in the URL address bar.
- **Barcode Not Detected:**
  - Ensure packaging is well lit and barcode lines are flat and unobstructed.
  - Tap the "Torch" toggle button if supported by your smartphone.
  - If the barcode is worn or curved, use the "Enter Barcode Manually" option or "Search by Name".
- **Open Food Facts Rate Limits / Offline:**
  - Open Food Facts API v3 applies community rate limits. If a 429 status code is returned, EATGOOD displays an informative notice and prompts the user to use manual entry or search the local catalogue.
- **CORS & Security Headers:**
  - FastAPI is configured with configurable `EATGOOD_CORS_ORIGINS` (defaults to local Vite and Uvicorn origins) and strict security headers:
    - `X-Content-Type-Options: nosniff`
    - `X-Frame-Options: SAMEORIGIN`
    - `Referrer-Policy: strict-origin-when-cross-origin`
    - `X-Request-ID: <uuid4>` for structured request tracing
- **Health & Readiness Checks:**
  - `GET /api/health`: Basic liveness probe.
  - `GET /api/ready`: Readiness probe verifying database connectivity and product catalogue loading.
- **Continuous Integration (CI):**
  - Managed via `.github/workflows/ci.yml` running Pytest (44 tests) and Vite frontend production build on pull requests and commits.
