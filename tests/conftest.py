"""Pytest configuration — disable compression middleware during tests."""
import os
import warnings

os.environ["TESTING"] = "1"

warnings.filterwarnings(
    "ignore",
    message="The 'app' shortcut is now deprecated",
    category=DeprecationWarning,
)

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)
