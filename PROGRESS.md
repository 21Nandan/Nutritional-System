# Progress

| Phase | Status | Notes |
|---|---|---|
| 0 Understand | Done | docs/history/PROJECT_MAP_PHASE0.md |
| 1 P0 breakage | Done in code; **live site unverified** | cross-user leaks, allergen paths, fail-fast loading, browser OCR, plain error codes; live check blocked by network |
| 2 Build/config | Done | one dependency source, pinned locks, uv.toml merged, Python ≥ 3.12, explicit Vercel install/build; npm `cache-dir` warning source unverified (likely a Vercel env var) |
| 3 Docs/claims | Done | README rewritten, docs/ folder, LICENSE, attribution, disclaimer banner, claims removed |
| 4 Data/images | Audited; labelled; no deletions | docs/DATA.md; image correctness needs a manual check with network access |
| 5 Nutrition logic | Partly done | basis bug fixed, allergens fixed, per-100 ml handled, flags from one source; thresholds marked unverified (docs/THRESHOLDS.md) |
| 6 Consumer UI | Partly done | pagination, URL filters, legend, line clamp, alt/lazy images, camera messages, titles; **Layer 1 simplification, Lighthouse and the 5-width visual check not done** |
| 7 Backend/security | Mostly done | Pydantic, routers, CORS, CSP/HSTS/Permissions-Policy, IP-based rate limits, OFF client, request IDs, no-PII logs, bandit/pip-audit clean; uploads removed (OCR is client-side) |
| 8 ML options | Report only | docs/ML_OPTIONS.md; circular model removed |
| 9 Tests/CI/hygiene | Done | 214 backend tests, 14 e2e, CI, CodeQL, Dependabot, pre-commit, Makefile, templates |

## Things only you can do

1. **Allow the network hosts** for future cloud sessions, so the live site can be checked from here:
   in the environment settings, add `eatgood26.vercel.app`, `vercel.com`, `api.vercel.com`,
   `world.openfoodfacts.org` and `images.openfoodfacts.org` under Allowed domains.
2. **Vercel** (dashboard → project → Settings), because no Vercel login is available here:
   - **Most important: Build and Deployment → Root Directory → clear it (use the repository root),
     then redeploy.** Every deployment since the original commit `f1faaf6` (06:20 UTC, before this
     work) has failed within 5–7 seconds, before any build ran. Vercel's PR comment marks the project
     as a monorepo (Root Directory set to a subfolder, almost certainly `frontend/`). The previous
     tool deleted the copies of `api/`, `data/` and `vercel.json` it had placed in `frontend/`, so
     Vercel finds nothing to deploy. The same build succeeds locally with the Vercel CLI from the
     repository root. Until this is changed, the live site keeps serving the last deployment from
     before 06:20.
   - Check Environment Variables for `npm_config_cache_dir` / `NPM_CONFIG_CACHE_DIR` (the likely
     source of "Unknown env config cache-dir") and delete it. Also delete `VISION_API_KEY`, which is
     no longer used.
   - Confirm "Automatically expose System Environment Variables" is on (Vercel Analytics depends on it).
   - Open the preview deployment for the pull request. If `/api/ready` returns 200, merge; then run the
     "Post-deploy smoke test" workflow on the production URL.
3. **GitHub settings** (Settings tab), because the tools available here cannot change repository settings:
   - Description: "Understand Indian packaged food labels: nutrition grade, personal fit, allergen
     checks, label scanning." Topics: `nutrition`, `food-labels`, `fastapi`, `react`, `india`,
     `open-food-facts`, `ocr`.
   - Code security: enable Dependabot alerts, secret scanning and push protection.
   - Branches → add a rule for `main`: require a pull request, require the CI checks ("Backend",
     "Frontend", "End-to-end", "Secret scan") to pass, block force pushes.
   - The `backup-antigravity-original` *branch* stands in for the requested tag (tag pushes were
     refused). Create a tag from it in the Releases UI if you want one.
4. **Decide about the data**: keep the demo catalogue (clearly labelled) or fund the work to import
   real Open Food Facts India data (docs/DECISIONS.md §4).
5. **Have the thresholds checked** against the WHO/FSSAI PDFs (docs/THRESHOLDS.md).
6. **Licence**: I chose MIT for the code. Change `LICENSE` if you prefer another.
