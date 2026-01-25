# Text-to-SQL AI Agent

A Python backend service for text-to-SQL (PostgreSQL) AI agents using FastAPI, LangGraph, ChromaDB, and Azure OpenAI.

## Quick Start

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your credentials

# Initialize and run
text-to-sql init
text-to-sql serve
```

## Features

- Natural language to SQL conversion
- LangGraph-based agent orchestration
- SSE streaming responses
- ChromaDB vector store for context retrieval
- SQL validation and safe execution
- Session management for conversation continuity

## CLI Commands

### SQL Pairs (Few-shot Examples)

SQL pairs are question-to-SQL mappings used for few-shot learning.

```bash
# Import SQL pairs from JSON file
text-to-sql sql-pairs import sample_data/sql_pairs.json
text-to-sql sql-pairs import sample_data/ec2_sql_pairs.json
text-to-sql sql-pairs import sample_data/tag_sql_pairs.json

# List imported pairs
text-to-sql sql-pairs list

# Search for similar pairs
text-to-sql sql-pairs search "find EC2 instances by tag"

# Clear all SQL pairs
text-to-sql sql-pairs clear -y
```

### Metadata (Domain Knowledge)

Metadata entries store business rules, domain terms, and context.

```bash
# Import metadata from JSON file
text-to-sql metadata import sample_data/metadata.json
text-to-sql metadata import sample_data/cloud_metadata.json

# List metadata entries
text-to-sql metadata list

# Search metadata
text-to-sql metadata search "tag query pattern"

# Clear all metadata
text-to-sql metadata clear -y
```

### Database Info (Schema)

Database info stores table schemas for SQL generation context.

```bash
# Introspect all tables from PostgreSQL
text-to-sql database-info introspect

# Import specific tables only
text-to-sql database-info import-tables aws_ec2 aws_s3 configuration_item

# List imported tables
text-to-sql database-info list

# Show table details
text-to-sql database-info show aws_ec2

# Search schema
text-to-sql database-info search "instance type"

# Clear all database info
text-to-sql database-info clear -y
```

### System Rules

View system-wide SQL generation rules.

```bash
# Show formatted rules
text-to-sql system-rules show

# Show raw JSON
text-to-sql system-rules show --raw
```

### Re-importing Data

The CLI supports safe re-imports. Entries are identified by deterministic IDs:
- SQL pairs: ID based on question text
- Metadata: ID based on title
- Database info: ID based on schema.table_name

Re-importing the same file will **update** existing entries (not create duplicates).

```bash
# Example: Re-import after updating SQL pairs
$ text-to-sql sql-pairs import sample_data/tag_sql_pairs.json
Added 2 SQL pairs, updated 9 SQL pairs
```

### Full Reset

To completely reset and re-import all data:

```bash
# Clear all collections
text-to-sql sql-pairs clear -y
text-to-sql metadata clear -y
text-to-sql database-info clear -y

# Re-import everything
text-to-sql sql-pairs import sample_data/sql_pairs.json
text-to-sql sql-pairs import sample_data/ec2_sql_pairs.json
text-to-sql sql-pairs import sample_data/tag_sql_pairs.json
text-to-sql metadata import sample_data/metadata.json
text-to-sql metadata import sample_data/cloud_metadata.json
text-to-sql database-info introspect
```
