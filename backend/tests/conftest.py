"""Test configuration: every test session gets its own throwaway SQLite database, and the
Open Food Facts catalogue is replaced by the invented test catalogue so no test needs the network."""

import os
import tempfile

import pytest

_tmp = tempfile.mkdtemp(prefix="eatgood-tests-")
os.environ["EATGOOD_DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["EATGOOD_ENV"] = "test"
os.environ["EATGOOD_RATE_LIMIT"] = "false"


@pytest.fixture(autouse=True)
def offline_catalogue(monkeypatch):
    """Product lookups, catalogue pages and alternatives come from tests/catalogue_fixture.py.

    Tests that need a specific Open Food Facts answer patch the same functions themselves.
    """
    from backend.routes import catalogue
    from backend.tests import catalogue_fixture as fx

    monkeypatch.setattr("backend.products.fetch_product_from_openfoodfacts", fx.fake_fetch)
    monkeypatch.setattr(catalogue, "browse_catalogue", fx.fake_browse)
    monkeypatch.setattr(catalogue, "alternative_candidates", fx.fake_alternative_candidates)
