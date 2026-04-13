"""Integration test configuration"""
import pytest


@pytest.fixture(scope="session")
def api_url():
    return "http://localhost:8100"
