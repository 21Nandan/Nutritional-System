# EATGOOD: AI-Powered Personalized Food Safety and Nutrition Assessment

> **Academic Experiential Learning (EL Phase-I) Project**  
> **Theme:** AI for Social Good  
> **Primary Objective:** Convert complex packaged-food labels into simple, transparent, evidence-based, and personalized assessments using international standards (WHO, FSSAI, Codex) and machine learning.

---

## 1. Quick Start & Execution

The application is completely self-contained and runs entirely locally.

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

### Run Automated Unit Tests:
```bash
PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_eatgood_core.py -v
```

---

## 2. Project Architecture & 3-Layer Assessment Engine

EATGOOD implements a modular, explainable hybrid architecture:

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
                  │  0–100 Score Tailored to User Objectives     │
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

### Layer 2: Personalized Suitability
- Custom 0–100 score tailored to the active user's stated goals:
  - **Reduce Sugar:** Rewards total sugars $\le 3\text{g}/100\text{g}$, penalizes $>10\text{g}$ and $>20\text{g}$.
  - **Reduce Sodium:** Rewards sodium $\le 140\text{mg}$, penalizes $>400\text{mg}$ and $>900\text{mg}$.
  - **Increase Fibre:** Rewards verified dietary fibre $\ge 3\text{g}$ and $\ge 6\text{g}/100\text{g}$.
  - **Increase Protein:** Rewards protein $\ge 7\text{g}$ and $\ge 12\text{g}/100\text{g}$.
  - **Balanced Choices:** Multi-nutrient balance incorporating healthy macro ratios.

### Layer 3: Ingredient, Allergen, and Additive Assessment
- Evaluates 10 major allergens: Milk, Soy, Gluten (Wheat), Peanuts, Tree Nuts, Eggs, Fish, Crustaceans, Sesame, Sulphites.
- **Critical Conflict Override:** If a product contains an allergen listed in the user's restrictions, the suitability score is **overridden to 0** and the product is excluded from recommendations.
- **Additive Registry:** Cross-references INS codes (e.g. INS 621 MSG, INS 102 Tartrazine, INS 211 Sodium Benzoate) against authoritative Codex/FSSAI regulatory context without unjustified toxicology panic.

---

## 3. Machine Learning Model Disclosure (Scientific Transparency)

- **Artifact:** `models/eatgood_model.joblib` & `models/model_metadata.json`
- **Training Script:** `src/train_model.py`
- **Training Set:** 1,500 simulated user-product recommendation pairs across 100 simulated user profiles (`data/personalization_examples.csv`).
- **Academic Disclaimer:** The reported 100% test accuracy is an artifact of evaluation on synthetically generated rule-based labels. It is **NOT** evidence of real-world clinical validity.
- **Integration Policy:** The ML model serves as an experimental architectural component demonstrating ML service integration alongside deterministic nutrition rules. Deterministic nutrition rules serve as the primary ground truth.

---

## 4. Dataset Governance & Calibrated Anomaly Counts

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

## 5. Offline OCR Label Extraction Architecture

The food label scanner (`backend/core/ocr_service.py` & `scripts/ocr_helper`) uses an offline local OCR engine:
- **100% Offline & Private:** Operates entirely locally without external paid cloud APIs.
- **Fast:** Executes text recognition in under 150ms.
- **Editable Confirmation Step:** Extracts metrics into an interactive form where the user confirms serving sizes and macro numbers before generating an assessment.

---

## 6. Literature Review References (EL Phase-I Presentation)

1. **Hammond et al. (2023):** *"Awareness, Use and Understanding of Nutrition Labels Among Children and Youth from Six Countries"* — Highlights that young consumers struggle with quantitative nutritional values, while interpretive front-of-pack labels significantly improve comprehension.
2. **Regulatory Policy Review (2023):** *"Global Regulatory Trends and Comparative Insights: Nutraceuticals in the USA, India, and Europe"* — Highlights the variance in international food safety standards.
3. **Shrestha et al. (2023):** *"Impact of Front-of-Pack Nutrition Labelling in Consumer Understanding and Use Across Socio-Economic Status"* — Demonstrates that graded front-of-pack labels reduce cognitive burden across socio-economic demographics.
4. **AI & Clinical Nutrition Review (2023):** *"Applications of Artificial Intelligence, Machine Learning, and Deep Learning in Nutrition: A Systematic Review"* — Surveys ML methods in dietary assessment while identifying data quality and interpretability as critical barriers.

---

## 7. Folder Structure

```
3rd sem EL/
├── backend/
│   ├── core/
│   │   ├── allergen_engine.py      # Layer 3 allergen & additive evaluation
│   │   ├── claims_detector.py      # Marketing claim auditor
│   │   ├── data_loader.py          # Multi-tier data loader
│   │   ├── ml_model.py             # ML model inference service
│   │   ├── nutrition_scoring.py    # 3-layer assessment logic
│   │   ├── ocr_service.py          # Vision OCR extraction parser
│   │   ├── recommender.py          # Goal-aligned alternatives engine
│   │   └── standards_registry.py   # WHO & FSSAI benchmarks
│   ├── database.py                 # SQLite local persistence
│   ├── main.py                     # FastAPI REST API & static bundle server
│   ├── tests/
│   │   └── test_eatgood_core.py    # Automated test suite (6 tests)
│   └── venv/                       # Python 3 virtual environment
├── data/
│   ├── raw/
│   │   └── packaged_foods_india.csv# 852 Indian products, 25 columns
│   ├── products_cleaned.csv
│   ├── products_standardized.csv
│   ├── data_quality_report.csv
│   ├── nutrition_review.csv        # 78 Atwater anomalies
│   ├── serving_size_review.csv     # 13 Macro > Serving anomalies
│   ├── users.csv                   # 100 simulated users
│   └── personalization_examples.csv# 1,500 training pairs
├── frontend/
│   ├── dist/                       # Production bundle (Vite)
│   ├── src/
│   │   ├── components/             # Navbar, Footer, ProfileModal
│   │   ├── pages/                  # Landing, Catalogue, Scanner, Assessment, Compare, Dashboard, Methodology, Audit
│   │   ├── App.jsx
│   │   ├── index.css               # Editorial Nature-inspired theme
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── models/
│   ├── eatgood_model.joblib        # Trained experimental model
│   └── model_metadata.json         # Scientific disclosures & schema
├── scripts/
│   ├── generate_initial_data.py    # Dataset generator & calibrator
│   ├── ocr_helper.swift            # Swift Apple Vision OCR script
│   └── ocr_helper                  # Compiled native OCR binary
├── src/
│   ├── train_model.py              # ML training script
│   └── recommend.py                # Standalone recommender engine
├── run.sh                          # One-click startup script
└── README.md
```

---

## 8. Responsible AI & Ethical Disclosure

- EATGOOD is strictly an educational and experiential learning prototype.
- It does not diagnose medical conditions or prescribe clinical nutritional therapies.
- The platform collects minimal profile data and operates 100% locally on the host machine without external telemetric transmissions.
