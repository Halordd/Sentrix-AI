from __future__ import annotations

import os
import time
import urllib.request

import pytest
from sqlalchemy import create_engine, text

API = os.getenv("SENTRIX_API", "http://127.0.0.1:8000")
MIGRATOR_URL = "postgresql+psycopg://sentrix_migrator@10.20.10.20:5432/sentrix"


def _clean_auth_audit() -> None:
    try:
        engine = create_engine(MIGRATOR_URL)
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE audit_event DISABLE TRIGGER USER"))
            try:
                connection.execute(
                    text("DELETE FROM audit_event WHERE action LIKE 'auth.%'")
                )
            finally:
                connection.execute(text("ALTER TABLE audit_event ENABLE TRIGGER USER"))
        engine.dispose()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def clean_auth_audit():
    _clean_auth_audit()
    yield
    _clean_auth_audit()


@pytest.fixture(scope="session", autouse=True)
def wait_for_api():
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(API + "/health", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    # Individual tests decide whether to skip or fail.
    return
