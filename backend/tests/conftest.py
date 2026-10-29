"""Test configuration: every test session gets its own throwaway SQLite database."""

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="eatgood-tests-")
os.environ["EATGOOD_DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["EATGOOD_ENV"] = "test"
os.environ["EATGOOD_RATE_LIMIT"] = "false"
