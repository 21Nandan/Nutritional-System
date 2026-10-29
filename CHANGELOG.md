# Changelog

## Unreleased

- Search ranking and data quality: deterministic ranking (relevance first, then completeness,
  ingredients/allergens, product identity and evidence of sale in India); products with severely
  incomplete or invalid key nutrition data are no longer listed; duplicates are merged. Applies to
  the catalogue, product search and healthier alternatives. "Sold in India" shown only on evidence.
- Removed user-facing source and community-contribution labels from product pages, barcode results,
  search and history. Community ratings and NOVA groups are unchanged.

- Catalogue: products now come from Open Food Facts (sold in India by default, or all countries). The
  852-product generated catalogue is quarantined in `data/quarantine/`, not deleted.
- Search: several words, an unfinished last word ("cadbury da"), extra spaces and barcodes work;
  clearing the search restores the list; the empty state appears only when nothing matches.
- Nutrient filters no longer overlap; they wrap on smaller screens.
- Comparison: restored. A stale or unavailable product is listed with a Remove option while the other
  products are still compared; the selection is kept in the address and the session.
- Scores: one consistent nutrition grade badge and Goal Match meter on product pages, catalogue cards,
  comparisons and alternatives, with an expandable explanation of how both are calculated.
- Product page: compact expandable additive boxes; the duplicate "Edit Values Now" button is removed.
- Profile page: tidier layout, Configure Profile as the main action, collapsible Recent Assessments
  and Saved Items.

- Label Scanner: removed the photo (OCR) option. Added "Search products", which searches the Open
  Food Facts world database through a new paginated endpoint, with results updating as you type;
  failures are shown as errors. Text search now uses search.openfoodfacts.org, because the old
  cgi/search.pl endpoint answers 503 ("unusually high demand"), checked from GitHub Actions on 2026-10-29.
- The website no longer names the data source in search, barcode or product screens; the ODbL
  licence notice stays in the footer, privacy policy and terms.
- Product page: the score calculation table is collapsed until you open it; the packaging photo
  section was removed.
- Removed the "About the data" page and the demo-data notices from the website (provenance is still
  documented in docs/DATA.md and in the data files).
- Phone layout: stacked profile columns, compact scanner tabs, shorter catalogue cards, search field
  and icon buttons no longer squashed.

## 1.1.0 (unreleased)

Safety and honesty overhaul after an audit of the code written by a previous AI tool
(see AUDIT_REPORT.md).

- Security: removed cross-visitor profile, history, saved-item and scan-log leaks. The profile now
  stays in the browser and is sent per request. Allergen checks on barcode lookups and alternatives
  now use the visitor's own allergens.
- Allergens: better matching (synonyms, regional names, hidden sources, "may contain", custom
  allergens) with fewer false positives; missing allergen data is never treated as safe.
- OCR moved into the browser (works on Vercel, photos never uploaded); impossible values need confirmation.
- Fail-fast catalogue loading, a real readiness check, explicit error states in every screen.
- Catalogue labelled as synthetic demo data; false "verified/authentic/offline" claims removed.
- Products with no stated measurement basis are no longer graded.
- Open Food Facts: production host only, retries, distinct error codes, "may contain" traces, no
  guessed categories.
- Pagination, URL filters, colour legend, self-hosted fonts, security headers.
- CI (lint, types, tests, e2e, audits, secret scan), CodeQL, Dependabot, Makefile.

## 1.0.0

Initial version generated with Antigravity (preserved on branch `backup-antigravity-original`).
