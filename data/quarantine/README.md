# Quarantined: synthetic demo catalogue

These files are **not used by EATGOOD**. Since 2026-10-29 the catalogue comes from Open Food Facts.

They are the former 852-product demo catalogue: real product names with randomly generated
nutrition values, ingredients, allergens and barcodes (`generate_initial_data.py`, seed 42,
reproduces them). They are kept here, not deleted, so the records stay available for audit.
Nothing in `backend/` reads this folder, and it is not deployed (see `vercel.json`).
