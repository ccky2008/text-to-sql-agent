"""DDL parser for extracting table schema from CREATE TABLE statements."""

import re
from dataclasses import dataclass, field


@dataclass
class ParsedColumn:
    """Parsed column information from DDL."""

    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    is_foreign_key: bool
    foreign_key_table: str | None
    foreign_key_column: str | None
    default_value: str | None
    description: str | None = None


@dataclass
class ParsedForeignKey:
    """Parsed foreign key relationship from DDL."""

    from_column: str
    to_table: str
    to_column: str


@dataclass
class ParsedTable:
    """Parsed table information from DDL."""

    schema_name: str
    table_name: str
    columns: list[ParsedColumn]
    primary_key_columns: list[str] = field(default_factory=list)
    foreign_keys: list[ParsedForeignKey] = field(default_factory=list)
    description: str | None = None


def parse_ddl(ddl: str, default_schema: str = "public") -> list[ParsedTable]:
    """Parse DDL statements and extract table information.

    Supports TypeORM and standard PostgreSQL CREATE TABLE syntax.

    Args:
        ddl: DDL string containing CREATE TABLE statements
        default_schema: Default schema name if not specified in DDL

    Returns:
        List of parsed table information
    """
    tables = []

    # Find all CREATE TABLE statements
    # Pattern matches: CREATE TABLE "schema"."table" or CREATE TABLE "table" or CREATE TABLE table
    # First, find the table name part
    create_pattern = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?'
        r'(?:"?(\w+)"?\.)?"?(\w+)"?\s*\(',
        re.IGNORECASE,
    )

    for match in create_pattern.finditer(ddl):
        schema_name = match.group(1) or default_schema
        table_name = match.group(2)

        # Find the matching closing parenthesis for the column definitions
        start_idx = match.end() - 1  # Position of opening (
        columns_def = _extract_parenthesized_content(ddl, start_idx)

        if columns_def:
            parsed_table = _parse_table_definition(schema_name, table_name, columns_def)
            if parsed_table:
                tables.append(parsed_table)

    return tables


def _extract_parenthesized_content(text: str, start_idx: int) -> str | None:
    """Extract content between matching parentheses, handling nesting."""
    if start_idx >= len(text) or text[start_idx] != "(":
        return None

    depth = 0
    content_start = start_idx + 1
    i = start_idx

    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[content_start:i]
        i += 1

    return None


def _parse_table_definition(schema_name: str, table_name: str, columns_def: str) -> ParsedTable | None:
    """Parse the column definitions within a CREATE TABLE statement."""
    columns: list[ParsedColumn] = []
    primary_key_columns: list[str] = []
    foreign_keys: list[ParsedForeignKey] = []

    # Split by comma, but handle nested parentheses (for DEFAULT expressions, etc.)
    parts = _split_column_definitions(columns_def)

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check for PRIMARY KEY constraint (table-level or within CONSTRAINT)
        # Handles: CONSTRAINT "name" PRIMARY KEY ("col") or PRIMARY KEY ("col")
        pk_match = re.search(
            r'PRIMARY\s+KEY\s*\(\s*([^)]+)\s*\)',
            part,
            re.IGNORECASE,
        )
        if pk_match:
            pk_cols = pk_match.group(1)
            for col in pk_cols.split(","):
                col_name = col.strip().strip('"').strip("'")
                if col_name:
                    primary_key_columns.append(col_name)
            continue

        # Check for FOREIGN KEY constraint (table-level)
        # Handles: CONSTRAINT "name" FOREIGN KEY ("col") REFERENCES "table" ("col")
        # or: FOREIGN KEY ("col") REFERENCES "table" ("col")
        fk_match = re.search(
            r'FOREIGN\s+KEY\s*\(\s*"?(\w+)"?\s*\)\s*REFERENCES\s+"?(\w+)"?\s*\(\s*"?(\w+)"?\s*\)',
            part,
            re.IGNORECASE,
        )
        if fk_match:
            foreign_keys.append(
                ParsedForeignKey(
                    from_column=fk_match.group(1),
                    to_table=fk_match.group(2),
                    to_column=fk_match.group(3),
                )
            )
            continue

        # Check for other CONSTRAINT types (UNIQUE, CHECK) - skip them
        if re.match(r'CONSTRAINT\s+', part, re.IGNORECASE):
            continue

        # Check for UNIQUE, CHECK at table level (without CONSTRAINT keyword)
        if re.match(r'(UNIQUE|CHECK)\s*\(', part, re.IGNORECASE):
            continue

        # Parse column definition
        column = _parse_column_definition(part)
        if column:
            columns.append(column)

    # Mark primary key columns
    for col in columns:
        if col.name in primary_key_columns:
            col.is_primary_key = True

    # Mark foreign key columns from table-level constraints
    fk_columns = {fk.from_column for fk in foreign_keys}
    for col in columns:
        if col.name in fk_columns and not col.is_foreign_key:
            col.is_foreign_key = True
            # Find the FK details
            for fk in foreign_keys:
                if fk.from_column == col.name:
                    col.foreign_key_table = fk.to_table
                    col.foreign_key_column = fk.to_column
                    break

    if not columns:
        return None

    return ParsedTable(
        schema_name=schema_name,
        table_name=table_name,
        columns=columns,
        primary_key_columns=primary_key_columns,
        foreign_keys=foreign_keys,
    )


def _split_column_definitions(columns_def: str) -> list[str]:
    """Split column definitions by comma, respecting parentheses nesting."""
    parts = []
    current = []
    depth = 0

    for char in columns_def:
        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)

    if current:
        parts.append("".join(current))

    return parts


def _parse_column_definition(col_def: str) -> ParsedColumn | None:
    """Parse a single column definition."""
    col_def = col_def.strip()
    if not col_def:
        return None

    # Pattern for column: "column_name" or column_name followed by data type
    # Handles quoted and unquoted column names
    col_pattern = re.match(
        r'"?(\w+)"?\s+(.+)',
        col_def,
        re.IGNORECASE | re.DOTALL,
    )

    if not col_pattern:
        return None

    col_name = col_pattern.group(1)
    rest = col_pattern.group(2).strip()

    # Extract data type (everything before constraints)
    # Data types can be: varchar, character varying, integer, uuid, TIMESTAMP WITH TIME ZONE, etc.
    data_type = _extract_data_type(rest)

    # Check for NOT NULL
    is_nullable = "NOT NULL" not in rest.upper()

    # Check for PRIMARY KEY (inline)
    is_primary_key = "PRIMARY KEY" in rest.upper()

    # Check for REFERENCES (inline foreign key)
    # Handles: REFERENCES "table"("column") or REFERENCES table(column)
    is_foreign_key = False
    foreign_key_table = None
    foreign_key_column = None

    ref_match = re.search(
        r'REFERENCES\s+"?(\w+)"?\s*\(\s*"?(\w+)"?\s*\)',
        rest,
        re.IGNORECASE,
    )
    if ref_match:
        is_foreign_key = True
        foreign_key_table = ref_match.group(1)
        foreign_key_column = ref_match.group(2)

    # Extract DEFAULT value
    default_value = _extract_default(rest)

    return ParsedColumn(
        name=col_name,
        data_type=data_type,
        is_nullable=is_nullable,
        is_primary_key=is_primary_key,
        is_foreign_key=is_foreign_key,
        foreign_key_table=foreign_key_table,
        foreign_key_column=foreign_key_column,
        default_value=default_value,
    )


def _extract_data_type(rest: str) -> str:
    """Extract the data type from the column definition remainder.

    Returns lowercase data type to match PostgreSQL information_schema format.
    """
    # Common PostgreSQL data types (including multi-word types)
    type_patterns = [
        r"(TIMESTAMP\s+WITH(?:OUT)?\s+TIME\s+ZONE)",
        r"(TIME\s+WITH(?:OUT)?\s+TIME\s+ZONE)",
        r"(DOUBLE\s+PRECISION)",
        r"(CHARACTER\s+VARYING(?:\s*\(\s*\d+\s*\))?)",
        r"(BIT\s+VARYING(?:\s*\(\s*\d+\s*\))?)",
        r"(\w+(?:\s*\(\s*[\d,\s]+\s*\))?)",  # type with optional precision/scale
    ]

    for pattern in type_patterns:
        match = re.match(pattern, rest, re.IGNORECASE)
        if match:
            # Normalize to lowercase to match PostgreSQL information_schema
            data_type = match.group(1).strip().lower()
            # Normalize whitespace in multi-word types
            data_type = " ".join(data_type.split())
            return data_type

    # Fallback: take first word (lowercase)
    first_word = rest.split()[0].lower() if rest.split() else "unknown"
    return first_word


def _extract_default(rest: str) -> str | None:
    """Extract DEFAULT value from column definition."""
    # Find DEFAULT keyword
    default_idx = rest.upper().find("DEFAULT")
    if default_idx == -1:
        return None

    # Start after "DEFAULT "
    start = default_idx + 7
    while start < len(rest) and rest[start] == " ":
        start += 1

    if start >= len(rest):
        return None

    # Extract the default value, handling function calls with parentheses
    result = []
    depth = 0
    i = start

    while i < len(rest):
        char = rest[i]

        # Track parenthesis depth for function calls like uuid_generate_v4()
        if char == "(":
            depth += 1
            result.append(char)
        elif char == ")":
            if depth > 0:
                depth -= 1
                result.append(char)
            else:
                break
        elif char == "," and depth == 0:
            break
        elif char == " " and depth == 0:
            # Check if next word is a constraint keyword
            remaining = rest[i:].strip().upper()
            if remaining.startswith(("NOT NULL", "NULL", "PRIMARY KEY", "UNIQUE", "CHECK", "REFERENCES", "CONSTRAINT")):
                break
            result.append(char)
        else:
            result.append(char)

        i += 1

    default_val = "".join(result).strip()
    return default_val if default_val else None
