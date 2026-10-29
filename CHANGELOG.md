# Changelog

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
