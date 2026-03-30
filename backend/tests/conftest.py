"""
Pytest configuration for FJAI-PromoterOS backend tests.

Scoring engine tests are pure unit tests — no DB or external services required.
API integration tests (future) will use a test database.
"""
import pytest


# Scoring tests require no fixtures — all pure functions.
# Future integration tests will add a db fixture here.
