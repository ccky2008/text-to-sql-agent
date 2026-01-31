"""Service for generating question suggestions."""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from text_to_sql.config import get_settings
from text_to_sql.services.vector_store import get_vector_store_service

logger = logging.getLogger(__name__)

INITIAL_QUESTIONS_PROMPT = """You are a helpful assistant that suggests questions users might want to ask about their cloud resources database.

CRITICAL: You must ONLY generate questions that can be answered using the EXACT tables and columns listed below. Do NOT ask about data, columns, or properties that are not explicitly listed in the schema.

Based on the database schema information below, generate exactly {n} natural language questions that users might want to ask. The questions should:
1. Be answerable ONLY using the available tables and columns listed below - do NOT invent or assume columns exist
2. Focus on the actual column names provided (e.g., if there is no "permissions" column, do not ask about permissions)
3. Be practical and relevant to cloud resource management
4. Cover different aspects: counts, filters by specific columns, aggregations, comparisons
5. Be clear and concise

## Available Database Schema (ONLY use these tables and columns)
{schema_info}

## Example Questions That Work (based on similar schemas)
{example_questions}

## Output Format
Return ONLY a JSON array of strings, with no additional text or explanation.

Generate {n} questions that can be answered using ONLY the columns listed above:"""

FOLLOWUP_QUESTIONS_PROMPT = """You are a helpful assistant that suggests follow-up questions based on a conversation about cloud resources.

CRITICAL: You must ONLY generate questions that can be answered using the columns shown in the SQL query and results. Do NOT ask about data or properties that were not in the query results.

Based on the conversation context below, generate exactly {n} relevant follow-up questions that the user might want to ask next. The questions should:
1. Be answerable using ONLY the columns/data shown in the results or available in related tables
2. Build upon what was just discussed - drill down, filter, aggregate differently
3. Reference actual column names or values seen in the results
4. Be natural next steps in the analysis
5. Be clear and concise

## Conversation Context
Original question: {original_question}

Generated SQL (shows available columns): {sql}

Query results summary: {results_summary}

## Available Schema Context
{schema_info}

## Output Format
Return ONLY a JSON array of strings, with no additional text or explanation.

Generate {n} follow-up questions using ONLY the available data:"""


class SuggestionsService:
    """Service for generating question suggestions using LLM."""

    def __init__(self) -> None:
        settings = get_settings()
        self._llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key.get_secret_value(),
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_deployment_name,
            temperature=0.3,  # Lower temperature for more precise, schema-focused questions
        )
        self._vector_store = get_vector_store_service()

    def _get_schema_summary(self) -> str:
        """Get a detailed summary of the database schema from vector store.

        Uses the full document text which contains column names and types.
        """
        try:
            tables = self._vector_store.list_database_info(limit=50)
            if not tables:
                return "No schema information available."

            schema_parts = []
            for table in tables:
                # Use the document field which contains detailed column info
                document = table.get("document", "")
                if document:
                    schema_parts.append(document)
                    schema_parts.append("")  # Empty line between tables
                else:
                    # Fallback to metadata if document not available
                    metadata = table.get("metadata", {})
                    table_name = metadata.get("table_name", "unknown")
                    column_names = metadata.get("column_names", "")
                    description = metadata.get("description", "")

                    schema_parts.append(f"Table: {table_name}")
                    if description:
                        schema_parts.append(f"Description: {description}")
                    if column_names:
                        schema_parts.append(f"Columns: {column_names}")
                    schema_parts.append("")

            return "\n".join(schema_parts).strip()
        except Exception as e:
            logger.warning(f"Failed to get schema summary: {e}")
            return "Schema information unavailable."

    def _get_example_questions(self, limit: int = 5) -> str:
        """Get example questions from SQL pairs that are known to work."""
        try:
            pairs = self._vector_store.list_sql_pairs(limit=limit)
            if not pairs:
                return "No example questions available."

            examples = []
            for pair in pairs:
                metadata = pair.get("metadata", {})
                question = metadata.get("question", "")
                if question:
                    examples.append(f"- {question}")

            return "\n".join(examples) if examples else "No example questions available."
        except Exception as e:
            logger.warning(f"Failed to get example questions: {e}")
            return "No example questions available."

    def _parse_questions_response(self, response: str, n: int) -> list[str]:
        """Parse LLM response to extract questions list."""
        try:
            # Try to parse as JSON
            questions = json.loads(response.strip())
            if isinstance(questions, list):
                return [str(q) for q in questions[:n]]
        except json.JSONDecodeError:
            pass

        # Fallback: try to extract lines that look like questions
        lines = response.strip().split("\n")
        questions = []
        for line in lines:
            line = line.strip()
            # Remove common prefixes like "1.", "-", "*"
            if line and (line[0].isdigit() or line[0] in "-*"):
                line = line.lstrip("0123456789.-*) ").strip()
            if line and "?" in line:
                # Extract the question part
                if '"' in line:
                    # Extract quoted text
                    start = line.find('"') + 1
                    end = line.rfind('"')
                    if start > 0 and end > start:
                        line = line[start:end]
                questions.append(line)

        return questions[:n]

    async def generate_initial_questions(self, n: int = 3) -> list[str]:
        """Generate initial questions based on database schema.

        Args:
            n: Number of questions to generate (max 3)

        Returns:
            List of suggested questions
        """
        n = min(n, 3)  # Cap at 3
        schema_info = self._get_schema_summary()
        example_questions = self._get_example_questions(limit=5)

        prompt = INITIAL_QUESTIONS_PROMPT.format(
            n=n,
            schema_info=schema_info,
            example_questions=example_questions,
        )

        messages = [
            SystemMessage(content="You are a helpful assistant that generates question suggestions. You MUST only suggest questions about data that exists in the provided schema."),
            HumanMessage(content=prompt),
        ]

        try:
            response = await self._llm.ainvoke(messages)
            content = response.content if isinstance(response.content, str) else str(response.content)
            questions = self._parse_questions_response(content, n)

            if not questions:
                # Fallback questions if parsing fails
                return self._get_fallback_initial_questions()[:n]

            return questions

        except Exception as e:
            logger.error(f"Failed to generate initial questions: {e}")
            return self._get_fallback_initial_questions()[:n]

    async def generate_followup_questions(
        self,
        original_question: str,
        sql: str | None,
        results: list[dict[str, Any]] | None,
        row_count: int | None,
        columns: list[str] | None,
        n: int = 3,
    ) -> list[str]:
        """Generate follow-up questions based on conversation context.

        Args:
            original_question: The user's original question
            sql: The generated SQL query
            results: Query results (first few rows)
            row_count: Total number of rows returned
            columns: Column names from the query
            n: Number of questions to generate (max 3)

        Returns:
            List of suggested follow-up questions
        """
        n = min(n, 3)  # Cap at 3

        # Build results summary
        results_summary_parts = []
        if row_count is not None:
            results_summary_parts.append(f"Returned {row_count} rows")
        if columns:
            results_summary_parts.append(f"Columns in result: {', '.join(columns)}")
        if results and len(results) > 0:
            # Include first few rows as sample
            sample = results[:3]
            results_summary_parts.append(f"Sample data: {json.dumps(sample, default=str)}")

        results_summary = "\n".join(results_summary_parts) if results_summary_parts else "No results"

        # Get schema context for better suggestions
        schema_info = self._get_schema_summary()

        prompt = FOLLOWUP_QUESTIONS_PROMPT.format(
            n=n,
            original_question=original_question,
            sql=sql or "No SQL generated",
            results_summary=results_summary,
            schema_info=schema_info,
        )

        messages = [
            SystemMessage(content="You are a helpful assistant that generates question suggestions. You MUST only suggest questions about data that exists in the query results or available schema."),
            HumanMessage(content=prompt),
        ]

        try:
            response = await self._llm.ainvoke(messages)
            content = response.content if isinstance(response.content, str) else str(response.content)
            questions = self._parse_questions_response(content, n)

            if not questions:
                return self._get_fallback_followup_questions(columns)[:n]

            return questions

        except Exception as e:
            logger.error(f"Failed to generate follow-up questions: {e}")
            return self._get_fallback_followup_questions(columns)[:n]

    @staticmethod
    def _get_fallback_initial_questions() -> list[str]:
        """Get fallback initial questions when LLM fails."""
        return [
            "How many cloud resources are in the database?",
            "List all resource types available",
            "Show me resources grouped by cloud provider",
        ]

    @staticmethod
    def _get_fallback_followup_questions(columns: list[str] | None) -> list[str]:
        """Get fallback follow-up questions when LLM fails.

        Args:
            columns: Column names from the previous query results
        """
        # Generate context-aware fallbacks based on available columns
        if columns:
            col_set = set(c.lower() for c in columns)
            questions = []

            if "resource_type" in col_set or "type" in col_set:
                questions.append("Can you break this down by resource type?")
            if "region" in col_set or "location" in col_set:
                questions.append("How does this vary by region?")
            if "tags" in col_set:
                questions.append("Which of these have specific tags?")
            if "created_at" in col_set or "create_time" in col_set:
                questions.append("Which were created most recently?")

            if questions:
                return questions[:3]

        # Generic fallbacks
        return [
            "Can you show me a count by resource type?",
            "Which resources were created most recently?",
            "Show me resources filtered by a specific criteria",
        ]


_suggestions_service: SuggestionsService | None = None


def get_suggestions_service() -> SuggestionsService:
    """Get singleton suggestions service instance."""
    global _suggestions_service
    if _suggestions_service is None:
        _suggestions_service = SuggestionsService()
    return _suggestions_service
