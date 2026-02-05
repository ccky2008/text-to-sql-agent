"""Streaming utilities for graph nodes."""

from collections.abc import Callable
from typing import Any

from langgraph.config import get_stream_writer


def _noop_writer(_data: Any) -> None:
    """No-op writer used when not running inside graph.astream()."""


def get_writer() -> Callable[[Any], None]:
    """Get a stream writer, returning a no-op if outside a graph runtime context.

    This allows nodes to be called directly (e.g., in tests or via ainvoke)
    without requiring a full streaming runtime.
    """
    try:
        return get_stream_writer()
    except RuntimeError:
        return _noop_writer
