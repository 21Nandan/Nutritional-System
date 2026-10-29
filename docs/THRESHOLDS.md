# Nutrition thresholds: sources and verification status

The single source of truth for thresholds is `backend/core/standards_registry.py`
(`CATEGORY_CALIBRATION_SPECS`, version `STANDARDS_REGISTRY_VERSION`). The grade, the catalogue
colour coding (`nutrient_flags`) and the filters all read from it.

## Verification status: **none of these thresholds has been verified against its cited document**

The previous tool recorded a "verification date" for every threshold, but nothing in the repository
shows that any number was ever checked. During this audit the WHO and PubMed Central hosts were blocked
from the work environment, so the original tables could not be read. Until someone compares each
number with the source PDF, treat every threshold as **heuristic, informed by** the cited document.
The registry now says this in a `source_check` field on every entry.

Corrections already made:

- The WHO SEARO Nutrient Profile Model was cited with ISBN 978-92-9022-589-8. The WHO publication
  page lists it as **978-92-9022-544-7** (https://www.who.int/publications/i/item/9789290225447).
  The citation and URL are corrected.

## Thresholds in use (per 100 g, or per 100 ml for beverages)

A value **above** the threshold counts as "high" for that nutrient.

| Category | Graded? | Basis | Sugars | Sat. fat | Sodium | Trans fat | Cited source(s) | Notes |
|---|---|---|---|---|---|---|---|---|
| Biscuits & Bakery | Yes | per 100 g | 10 g | 4 g | 300 mg | 0.1 g | WHO SEARO 2017 (cat. 3); FSSAI draft INR 2022 | unverified |
| Snacks | Yes | per 100 g | 10 g | 4 g | 400 mg | 0.1 g | WHO SEARO 2017 (cat. 4); FSSAI draft INR 2022 | unverified |
| Breakfast Cereals | Yes | per 100 g | 15 g | 2 g | 300 mg | 0.1 g | WHO SEARO 2017 (cat. 1); FSSAI draft INR 2022 | unverified |
| Packaged Beverages | Yes | per 100 ml | 5 g | 0 g | 80 mg | 0.1 g | WHO guidance on sugar-sweetened beverages (2020); FSSAI draft INR | **sat. fat 0 g and sodium 80 mg have no cited basis → heuristic** |
| Instant Foods | Yes | per 100 g | 5 g | 4 g | 450 mg | 0.1 g | WHO SEARO 2017 (cat. 6); FSSAI draft INR | unverified |
| Dairy | Yes | per 100 g | 10 g | 4 g | 300 mg | 0.1 g | WHO SEARO 2017 (cat. 2); FSSAI draft INR | unverified; dairy drinks declared per 100 ml are compared with per-100 g numbers |
| Chocolates & Sweets | Yes, **EATGOOD's own method** | per 100 g | 22.5 g | 5 g | 600 mg | 0.1 g | Reference points: UK DH/FSA front-of-pack "high" cut-offs per 100 g (sugars 22.5 g, sat. fat 5 g, salt 1.5 g) | **not an official WHO or FSSAI grade**; labelled as EATGOOD's own method wherever the grade is shown |
| Condiments & Spreads | No | — | — | — | — | — | WHO SEARO 2017; Codex CAC/GL 2-1985 | no grade, explained in the UI |

### Chocolates & Sweets: EATGOOD's own method

No official body publishes A–E limits for confectionery; the WHO SEARO model excludes it from
marketing to children altogether. EATGOOD therefore grades chocolates and sweets with its own
limits, using the UK front-of-pack "high" cut-offs per 100 g as reference points. Products are
scored with the same points, formula and grade bands as every other category, so the grade follows
each product's values: for example, a typical milk chocolate (about 55 g sugars and 18 g saturated
fat) gets E, a sugar-free mint B. Energy, sugars, saturated fat and sodium are required; without
them, or with contradictory values, the product is not graded. Pages, cards, comparison and
alternatives say "EATGOOD's own method, not an official grade" next to these grades.

Other fixed numbers used in scoring and parsing:

| Rule | Value | Source | Status |
|---|---|---|---|
| Salt → sodium | sodium (mg) = salt (g) × 400, i.e. salt ÷ 2.5 | standard chemistry (Na is 39.3 % of NaCl) | correct |
| Atwater energy check | 4 kcal/g carbohydrate and protein, 9 kcal/g fat; flag if off by > 60 kcal (label parser) or > 50 kcal / 25 % (data report) | general factors (FAO) | two different tolerances; heuristic |
| Personal goal rules (e.g. sugar ≤ 5 g rewarded, > 20 g penalised) | see `assess_personalized_suitability` | none; labelled "EATGOOD Dietary Goal Rule" in the UI | **heuristic** |
| Catalogue "Healthier preset" filter | sugar ≤ 10 g, sodium ≤ 400 mg, sat. fat ≤ 4 g | mirrors the Snacks thresholds | heuristic convenience filter |

## Basis handling (verified in code and tests)

- Values declared **per serving** are converted to per 100 g/ml using the serving size; with no serving
  size the product is not graded.
- Values with **no stated basis** are not graded (fixed in this audit; it previously applied per-100 g
  thresholds to 40 such products).
- Missing values are never treated as zero; the UI shows "Not stated".

## Decisions owed

1. Someone with access to the original PDFs should check each number above and replace "unverified"
   with page references, or change the numbers. Grades must not change without that review.
2. Decide whether beverages should keep the 0 g saturated-fat and 80 mg sodium limits (no source).
