"""Tests for clarification flow."""

from text_to_sql.agents.nodes.sql_generator import _parse_sql_response
from text_to_sql.agents.graph import should_validate_or_respond, should_retry


class TestParseClarification:
    """Test _parse_sql_response with NEEDS_CLARIFICATION prefix."""

    def test_needs_clarification_parsed(self):
        """Test that [NEEDS_CLARIFICATION] prefix is detected."""
        content = "[NEEDS_CLARIFICATION] Which type of resources are you interested in?"
        sql, message, special_type = _parse_sql_response(content)

        assert sql is None
        assert special_type == "NEEDS_CLARIFICATION"
        assert "Which type of resources" in message

    def test_needs_clarification_strips_prefix(self):
        """Test that the prefix is stripped from the message."""
        content = "[NEEDS_CLARIFICATION] Could you specify the region?"
        _, message, special_type = _parse_sql_response(content)

        assert special_type == "NEEDS_CLARIFICATION"
        assert message == "Could you specify the region?"

    def test_needs_clarification_with_whitespace(self):
        """Test that leading whitespace is handled."""
        content = "  [NEEDS_CLARIFICATION] Please clarify your query."
        _, message, special_type = _parse_sql_response(content)

        assert special_type == "NEEDS_CLARIFICATION"
        assert message == "Please clarify your query."

    def test_regular_sql_not_affected(self):
        """Test that normal SQL responses are not affected."""
        content = "```sql\nSELECT * FROM ec2;\n```\nThis query returns all EC2 instances."
        sql, explanation, special_type = _parse_sql_response(content)

        assert sql == "SELECT * FROM ec2;"
        assert special_type is None

    def test_out_of_scope_still_works(self):
        """Test that OUT_OF_SCOPE still works correctly."""
        content = "[OUT_OF_SCOPE] I can only help with cloud resources."
        sql, message, special_type = _parse_sql_response(content)

        assert sql is None
        assert special_type == "OUT_OF_SCOPE"

    def test_read_only_still_works(self):
        """Test that READ_ONLY still works correctly."""
        content = "[READ_ONLY] Data modifications are not permitted."
        sql, message, special_type = _parse_sql_response(content)

        assert sql is None
        assert special_type == "READ_ONLY"


class TestShouldValidateOrRespondClarification:
    """Test should_validate_or_respond routing for NEEDS_CLARIFICATION."""

    def test_routes_to_responder(self):
        """Test that NEEDS_CLARIFICATION routes to responder."""
        state = {"special_response_type": "NEEDS_CLARIFICATION"}
        assert should_validate_or_respond(state) == "responder"

    def test_out_of_scope_still_routes_to_responder(self):
        """Test that OUT_OF_SCOPE still routes to responder."""
        state = {"special_response_type": "OUT_OF_SCOPE"}
        assert should_validate_or_respond(state) == "responder"

    def test_normal_routes_to_validator(self):
        """Test that normal state routes to validator."""
        state = {"special_response_type": None}
        assert should_validate_or_respond(state) == "validator"

    def test_tool_call_routes_to_tool_executor(self):
        """Test that pending tool call routes to tool_executor."""
        state = {"pending_tool_call": {"name": "test"}, "special_response_type": None}
        assert should_validate_or_respond(state) == "tool_executor"


class TestShouldRetryClarification:
    """Test should_retry routing for NEEDS_CLARIFICATION."""

    def test_no_retry_for_clarification(self):
        """Test that NEEDS_CLARIFICATION skips retry and goes to responder."""
        state = {
            "special_response_type": "NEEDS_CLARIFICATION",
            "is_valid": False,
            "retry_count": 0,
        }
        assert should_retry(state) == "responder"

    def test_no_retry_for_out_of_scope(self):
        """Test that OUT_OF_SCOPE skips retry."""
        state = {
            "special_response_type": "OUT_OF_SCOPE",
            "is_valid": False,
            "retry_count": 0,
        }
        assert should_retry(state) == "responder"

    def test_retry_for_normal_failure(self):
        """Test that normal validation failure retries."""
        state = {
            "special_response_type": None,
            "is_valid": False,
            "retry_count": 0,
        }
        assert should_retry(state) == "sql_generator"
