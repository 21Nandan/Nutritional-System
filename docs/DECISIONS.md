# Architecture decisions

Each decision lists the options considered, with cost, effort and risk, and what would break if
nothing were done. Rule applied: choose the cheapest option that works and avoid migrations.

## 1. Label photo reading (OCR): **removed** (2026-10-29)

Label scanning first ran on the server with `pytesseract`, which cannot work on Vercel, and was then
moved into the browser with tesseract.js. At the owner's request it was removed: the Label Scanner now
offers product search (Open Food Facts world database, `GET /api/products/search/openfoodfacts`),
barcode lookup and manual entry. This removed a 7 MB first-scan download, the
`'wasm-unsafe-eval'` CSP exception and the label-text parser. The previous implementation is in git
history (commit `2d93886` and earlier).

## 2. User data / database: **browser storage + stateless API** (chosen)

Problem: SQLite was copied to `/tmp` on each serverless instance, so profiles, history and saved items
disappeared unpredictably, and different instances held different data. Worse, the data was shared
across visitors:
- A new visitor inherited the default profile (anyone could overwrite it, including its allergens).
- `GET /api/history` returned everyone's history, and `DELETE /api/history` erased it.
- Saved products and scan logs were global.

| Option | Monthly cost | Effort | Risk | Notes |
|---|---|---|---|---|
| **A. localStorage per device; profile sent per request** | $0 | 1 day | data is per device and is lost if the user clears site data | no accounts, nothing personal stored on the server |
| B. Anonymous device ID + hosted Postgres/libSQL (Neon, Turso free tiers) | $0 on free tiers | 2–3 days | the device ID is a bearer secret; adds a database to secure and maintain | needed later only if sync across devices is wanted |
| C. Real accounts (Supabase Auth + Postgres) | $0 on free tier | 4–5 days | passwords, email and GDPR/DPDP obligations | overkill for an informational tool |

If nothing were done, cross-user data exposure and silent data loss would continue.

SQLite remains only for the Open Food Facts lookup cache and unmoderated contributions, both safe to
lose. On Vercel, contributions are therefore **ephemeral** (per instance). Moving them to a hosted
database is decision 4 below.

## 3. Catalogue serving: **bundle the CSV files with the function** (kept)

The CSVs are bundled through `vercel.json → functions.includeFiles` and loaded at startup. The loader
now fails fast (missing file, empty file or row-count mismatch raises), so a broken bundle produces a
clear error in the Vercel logs and a 500 response, instead of an empty catalogue. A static JSON
catalogue would remove pandas from the cold start, but it is a larger rewrite with no user-visible
benefit at 852 rows.

## 4. Open decisions

- **Real data**: replace the synthetic catalogue with real products. The cheapest option is an Open
  Food Facts India export (ODbL, free, incomplete and community-checked). It needs import scripts,
  attribution and review.
- **Contributions persistence**: on Vercel they are lost when an instance recycles. Options: drop the
  feature in production (free); use a free hosted Postgres with a moderation queue (1–2 days); or
  point users to contribute on Open Food Facts directly (free, recommended).
- **Auth**: not needed while the server stores no personal data.
