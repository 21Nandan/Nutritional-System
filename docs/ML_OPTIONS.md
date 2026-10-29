# ML / AI options (report only; nothing here is built)

Principles: grades, scores and allergen decisions stay deterministic, and no model output changes them.
Use own or local models first, and paid APIs only where they clearly win.

| # | Item | Approach | Evidence so far | Monthly cost | Effort | Privacy | Recommendation |
|---|---|---|---|---|---|---|---|
| 1 | Old sklearn "personalization" model | **Removed** from the product path | It was trained on 1,500 rule-generated pairs (accuracy 1.0 is circular); it never loaded on Vercel because scikit-learn wasn't installed | $0 | done | — | Keep removed. Retrain only with real labels and held-out metrics. |
| 2 | Label OCR | tesseract.js in the browser (**done**, see DECISIONS.md) | Rendered test label read correctly in 1–2 s | $0 | done | photo stays on the device | Next: build a real photo fixture set (blur, glare, curved pack, Hindi/bilingual) and measure. Add the `hin` model only if fixtures show a need (+~2 MB). |
| 3 | Vision-API fallback | Google Cloud Vision only when browser confidence is low, with consent | Not measured | $0 for ≤ 1,000/month, then $1.50 per 1,000 | 1 day | photo sent to Google (needs a consent notice) | Only after the fixture set shows tesseract.js failing often. Needs a server-side key, spend cap, rate limit and cache. |
| 4 | Semantic search | small sentence-embedding model run offline; vectors shipped as a static file (852 × 384 floats ≈ 1.3 MB); rapidfuzz for typos | Today's keyword "semantic" parser works for the tested phrases | $0 | 1–2 days | none | Worth it once the catalogue is real data; with synthetic data it adds little. |
| 5 | Alternatives | rank by nutrient-vector distance **after** allergen and preference exclusion | Exclusion-first is already enforced and tested | $0 | 0.5 day | none | Do it together with real data. |
| 6 | Explanations | rule-based templates (current); optional LLM wording grounded strictly on computed values | — | $0 (rules) / about $1–5 for an LLM at low traffic | 1 day | product values sent to an LLM provider | Keep rules. An LLM only rewords and never adds facts. |
| 7 | Image mismatch check | run CLIP locally once to compare each photo with its product name | Couldn't run: Open Food Facts images were blocked in the work environment | $0 | 2 hours | none | Run locally, then review the 38 flagged rows by hand (see docs/DATA.md). |
