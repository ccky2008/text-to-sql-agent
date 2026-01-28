"""Tests for query cache service."""

import time

import pytest

from text_to_sql.services.query_cache import QueryCache, get_query_cache


class TestQueryCache:
    """Test QueryCache functionality."""

    def test_store_and_get(self):
        """Test storing and retrieving a query."""
        cache = QueryCache(ttl_seconds=60)
        sql = "SELECT * FROM users"
        session_id = "test-session"

        token = cache.store(sql, session_id)

        assert token is not None
        assert len(token) > 20  # Secure token should be reasonably long

        cached = cache.get(token)
        assert cached is not None
        assert cached.sql == sql
        assert cached.session_id == session_id

    def test_get_nonexistent_token(self):
        """Test retrieving a non-existent token returns None."""
        cache = QueryCache()

        result = cache.get("nonexistent-token")

        assert result is None

    def test_token_expiration(self):
        """Test that tokens expire after TTL."""
        cache = QueryCache(ttl_seconds=1)  # 1 second TTL
        sql = "SELECT 1"

        token = cache.store(sql, "session")

        # Should be valid immediately
        assert cache.get(token) is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired now
        assert cache.get(token) is None

    def test_unique_tokens(self):
        """Test that each store creates a unique token."""
        cache = QueryCache()
        sql = "SELECT 1"

        token1 = cache.store(sql, "session1")
        token2 = cache.store(sql, "session2")

        assert token1 != token2

    def test_max_entries_cleanup(self):
        """Test that cache cleans up when max entries exceeded."""
        cache = QueryCache(ttl_seconds=1, max_entries=5)

        # Store entries that will expire
        for i in range(5):
            cache.store(f"SELECT {i}", "session")

        # Wait for expiration
        time.sleep(1.1)

        # Store new entry - should trigger cleanup
        token = cache.store("SELECT new", "session")

        # New entry should be valid
        assert cache.get(token) is not None

        # Cache should have been cleaned
        assert len(cache._cache) <= 5


class TestGetQueryCache:
    """Test singleton query cache."""

    def test_singleton(self):
        """Test that get_query_cache returns the same instance."""
        cache1 = get_query_cache()
        cache2 = get_query_cache()

        assert cache1 is cache2

    def test_store_retrieve_via_singleton(self):
        """Test storing and retrieving via singleton."""
        cache = get_query_cache()
        sql = "SELECT * FROM test_singleton"

        token = cache.store(sql, "test-session")
        cached = cache.get(token)

        assert cached is not None
        assert cached.sql == sql
