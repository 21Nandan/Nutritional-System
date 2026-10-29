"""
Runs the real EATGOOD app with the invented test catalogue in place of Open Food Facts, for the
browser tests and for trying the site without network access:

    EATGOOD_RATE_LIMIT=false python -m backend.tests.serve_offline [port]

Never used in production. Product lookups, catalogue pages and alternatives come from
tests/catalogue_fixture.py, exactly as in the backend tests.
"""

import sys

import uvicorn

from backend import products
from backend.main import app
from backend.routes import catalogue
from backend.tests import catalogue_fixture as fx

products.fetch_product_from_openfoodfacts = fx.fake_fetch
catalogue.browse_catalogue = fx.fake_browse
catalogue.alternative_candidates = fx.fake_alternative_candidates

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
