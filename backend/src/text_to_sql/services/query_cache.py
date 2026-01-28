"""Query token cache for secure CSV downloads.

Stores validated SQL server-side and returns tokens to clients.
This prevents the CSV endpoint from accepting arbitrary SQL.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass
from threading import Lock


@dataclass
class CachedQuery:
    """A cached validated SQL query."""

    sql: str
    created_at: float
    session_id: str


class QueryCache:
    """In-memory cache for validated SQL queries.

    Tokens are secure random strings that map to validated SQL.
    Entries expire after TTL seconds.
    """

    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 10000):
        self._cache: dict[str, CachedQuery] = {}
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._lock = Lock()

    def store(self, sql: str, session_id: str) -> str:
        """Store validated SQL and return a secure token.

        Args:
            sql: The validated SQL query
            session_id: The session that validated this query

        Returns:
            A secure token that can be used to retrieve the SQL
        """
        # Generate secure token
        token = secrets.token_urlsafe(32)

        with self._lock:
            # Clean expired entries if cache is getting full
            if len(self._cache) >= self._max_entries:
                self._cleanup_expired()

            self._cache[token] = CachedQuery(
                sql=sql,
                created_at=time.time(),
                session_id=session_id,
            )

        return token

    def get(self, token: str) -> CachedQuery | None:
        """Retrieve a cached query by token.

        Args:
            token: The token returned from store()

        Returns:
            The cached query, or None if not found or expired
        """
        with self._lock:
            entry = self._cache.get(token)
            if entry is None:
                return None

            # Check if expired
            if time.time() - entry.created_at > self._ttl:
                del self._cache[token]
                return None

            return entry

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        now = time.time()
        expired = [
            token
            for token, entry in self._cache.items()
            if now - entry.created_at > self._ttl
        ]
        for token in expired:
            del self._cache[token]


# Singleton instance
_query_cache: QueryCache | None = None


def get_query_cache() -> QueryCache:
    """Get the singleton query cache instance."""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache
