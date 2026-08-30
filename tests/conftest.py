"""Pytest configuration for the SIH PS83 backend.

The test suite runs against the live development database using
FastAPI's TestClient. TestClient opens a fresh event loop per request
which is incompatible with pooled asyncpg connections on Windows, so
the engine is forced to NullPool (DB_POOL_SIZE=0) before the app is
imported by any test module.
"""

import os

os.environ.setdefault("DB_POOL_SIZE", "0")
os.environ.setdefault("NOTIFICATION_DRY_RUN", "true")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")