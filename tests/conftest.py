"""Pytest configuration and fixtures."""

import os

import pytest


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch):
    """Set test environment variables."""
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
    monkeypatch.setenv("POSTGRES_DATABASE", "test_db")
    monkeypatch.setenv("POSTGRES_USER", "test_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")
    monkeypatch.setenv("CHROMADB_PERSIST_DIRECTORY", "/tmp/chroma_test")


@pytest.fixture
def sample_sql_pair():
    """Sample SQL pair for testing."""
    return {
        "question": "Show all users",
        "sql_query": "SELECT * FROM users",
    }


@pytest.fixture
def sample_metadata():
    """Sample metadata for testing."""
    return {
        "title": "Active User Definition",
        "content": "A user who logged in within 30 days",
        "category": "domain_term",
        "related_tables": ["users"],
        "keywords": ["active", "user"],
    }
