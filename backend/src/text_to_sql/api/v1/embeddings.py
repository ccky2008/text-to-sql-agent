"""Embeddings management API endpoints."""

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from text_to_sql.models.data_sources import (
    ColumnInfo,
    MetadataEntry,
    Relationship,
    SQLPair,
    TableInfo,
)
from text_to_sql.models.embeddings import (
    BulkCreateResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
    BulkUpdateResponse,
    ColumnInfoResponse,
    DatabaseInfoBulkUpdateItem,
    DatabaseInfoCreate,
    DatabaseInfoListResponse,
    DatabaseInfoResponse,
    DatabaseInfoUpdate,
    DDLImportRequest,
    DDLImportResponse,
    MetadataBulkUpdateItem,
    MetadataCreate,
    MetadataListResponse,
    MetadataResponse,
    MetadataUpdate,
    RelationshipResponse,
    SQLPairBulkUpdateItem,
    SQLPairCreate,
    SQLPairListResponse,
    SQLPairResponse,
    SQLPairUpdate,
)
from text_to_sql.services.vector_store import get_vector_store_service

router = APIRouter(prefix="/embeddings")


# ============================================================================
# SQL Pairs Endpoints
# ============================================================================


@router.get("/sql-pairs", response_model=SQLPairListResponse)
async def list_sql_pairs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> SQLPairListResponse:
    """List all SQL pairs with pagination."""
    vector_store = get_vector_store_service()
    offset = (page - 1) * page_size

    items = vector_store.list_sql_pairs(limit=page_size, offset=offset)
    total = vector_store.get_sql_pairs_count()

    return SQLPairListResponse(
        items=[
            SQLPairResponse(
                id=item["metadata"]["id"],
                question=item["metadata"]["question"],
                sql_query=item["metadata"]["sql_query"],
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
        has_prev=page > 1,
    )


@router.get("/sql-pairs/{pair_id}", response_model=SQLPairResponse)
async def get_sql_pair(pair_id: str) -> SQLPairResponse:
    """Get a single SQL pair by ID."""
    vector_store = get_vector_store_service()
    item = vector_store.get_sql_pair(pair_id)

    if not item:
        raise HTTPException(status_code=404, detail=f"SQL pair not found: {pair_id}")

    return SQLPairResponse(
        id=item["metadata"]["id"],
        question=item["metadata"]["question"],
        sql_query=item["metadata"]["sql_query"],
    )


@router.post("/sql-pairs", response_model=SQLPairResponse, status_code=201)
async def create_sql_pair(data: SQLPairCreate) -> SQLPairResponse:
    """Create a new SQL pair."""
    vector_store = get_vector_store_service()

    pair = SQLPair(question=data.question, sql_query=data.sql_query)
    pair_id, is_update = vector_store.add_sql_pair(pair)

    return SQLPairResponse(
        id=pair_id,
        question=data.question,
        sql_query=data.sql_query,
    )


@router.post("/sql-pairs/bulk", response_model=BulkCreateResponse)
async def bulk_create_sql_pairs(data: list[SQLPairCreate]) -> BulkCreateResponse:
    """Bulk create SQL pairs."""
    vector_store = get_vector_store_service()

    created = 0
    updated = 0
    failed = 0
    errors: list[str] = []

    for item in data:
        try:
            pair = SQLPair(question=item.question, sql_query=item.sql_query)
            _, is_update = vector_store.add_sql_pair(pair)
            if is_update:
                updated += 1
            else:
                created += 1
        except Exception as e:
            failed += 1
            errors.append(f"Failed to create SQL pair '{item.question[:50]}...': {e}")

    return BulkCreateResponse(created=created, updated=updated, failed=failed, errors=errors)


@router.put("/sql-pairs/{pair_id}", response_model=SQLPairResponse)
async def update_sql_pair(pair_id: str, data: SQLPairUpdate) -> SQLPairResponse:
    """Update a SQL pair."""
    vector_store = get_vector_store_service()

    result = vector_store.update_sql_pair(
        pair_id=pair_id,
        question=data.question,
        sql_query=data.sql_query,
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"SQL pair not found: {pair_id}")

    return SQLPairResponse(
        id=result["metadata"]["id"],
        question=result["metadata"]["question"],
        sql_query=result["metadata"]["sql_query"],
    )


@router.put("/sql-pairs/bulk/update", response_model=BulkUpdateResponse)
async def bulk_update_sql_pairs(data: list[SQLPairBulkUpdateItem]) -> BulkUpdateResponse:
    """Bulk update SQL pairs."""
    vector_store = get_vector_store_service()

    updated = 0
    not_found: list[str] = []
    errors: list[str] = []

    for item in data:
        try:
            result = vector_store.update_sql_pair(
                pair_id=item.id,
                question=item.question,
                sql_query=item.sql_query,
            )
            if result:
                updated += 1
            else:
                not_found.append(item.id)
        except Exception as e:
            errors.append(f"Failed to update SQL pair '{item.id}': {e}")

    return BulkUpdateResponse(updated=updated, not_found=not_found, errors=errors)


@router.delete("/sql-pairs/{pair_id}")
async def delete_sql_pair(pair_id: str) -> dict:
    """Delete a SQL pair."""
    vector_store = get_vector_store_service()

    if not vector_store.delete_sql_pair(pair_id):
        raise HTTPException(status_code=404, detail=f"SQL pair not found: {pair_id}")

    return {"status": "deleted", "id": pair_id}


@router.delete("/sql-pairs/bulk/delete", response_model=BulkDeleteResponse)
async def bulk_delete_sql_pairs(data: BulkDeleteRequest) -> BulkDeleteResponse:
    """Bulk delete SQL pairs."""
    vector_store = get_vector_store_service()

    deleted, not_found = vector_store.delete_sql_pairs_bulk(data.ids)

    return BulkDeleteResponse(deleted=deleted, not_found=not_found)


# ============================================================================
# Metadata Endpoints
# ============================================================================


def _parse_metadata_response(item: dict) -> MetadataResponse:
    """Parse metadata item to response model."""
    meta = item["metadata"]
    related_tables = meta.get("related_tables", "")
    keywords = meta.get("keywords", "")
    created_at_str = meta.get("created_at")

    return MetadataResponse(
        id=meta["id"],
        title=meta["title"],
        content=meta["content"],
        category=meta["category"],
        related_tables=related_tables.split(",") if related_tables else [],
        keywords=keywords.split(",") if keywords else [],
        created_at=datetime.fromisoformat(created_at_str) if created_at_str else None,
    )


@router.get("/metadata", response_model=MetadataListResponse)
async def list_metadata(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> MetadataListResponse:
    """List all metadata entries with pagination."""
    vector_store = get_vector_store_service()
    offset = (page - 1) * page_size

    items = vector_store.list_metadata(limit=page_size, offset=offset)
    total = vector_store.get_metadata_count()

    return MetadataListResponse(
        items=[_parse_metadata_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
        has_prev=page > 1,
    )


@router.get("/metadata/{entry_id}", response_model=MetadataResponse)
async def get_metadata(entry_id: str) -> MetadataResponse:
    """Get a single metadata entry by ID."""
    vector_store = get_vector_store_service()
    item = vector_store.get_metadata_entry(entry_id)

    if not item:
        raise HTTPException(status_code=404, detail=f"Metadata entry not found: {entry_id}")

    return _parse_metadata_response(item)


@router.post("/metadata", response_model=MetadataResponse, status_code=201)
async def create_metadata(data: MetadataCreate) -> MetadataResponse:
    """Create a new metadata entry."""
    vector_store = get_vector_store_service()

    entry = MetadataEntry(
        title=data.title,
        content=data.content,
        category=data.category,
        related_tables=data.related_tables,
        keywords=data.keywords,
    )
    entry_id, _ = vector_store.add_metadata(entry)

    return MetadataResponse(
        id=entry_id,
        title=data.title,
        content=data.content,
        category=data.category.value,
        related_tables=data.related_tables,
        keywords=data.keywords,
        created_at=entry.created_at,
    )


@router.post("/metadata/bulk", response_model=BulkCreateResponse)
async def bulk_create_metadata(data: list[MetadataCreate]) -> BulkCreateResponse:
    """Bulk create metadata entries."""
    vector_store = get_vector_store_service()

    created = 0
    updated = 0
    failed = 0
    errors: list[str] = []

    for item in data:
        try:
            entry = MetadataEntry(
                title=item.title,
                content=item.content,
                category=item.category,
                related_tables=item.related_tables,
                keywords=item.keywords,
            )
            _, is_update = vector_store.add_metadata(entry)
            if is_update:
                updated += 1
            else:
                created += 1
        except Exception as e:
            failed += 1
            errors.append(f"Failed to create metadata '{item.title[:50]}...': {e}")

    return BulkCreateResponse(created=created, updated=updated, failed=failed, errors=errors)


@router.put("/metadata/{entry_id}", response_model=MetadataResponse)
async def update_metadata(entry_id: str, data: MetadataUpdate) -> MetadataResponse:
    """Update a metadata entry."""
    vector_store = get_vector_store_service()

    result = vector_store.update_metadata(
        entry_id=entry_id,
        title=data.title,
        content=data.content,
        category=data.category.value if data.category else None,
        related_tables=data.related_tables,
        keywords=data.keywords,
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"Metadata entry not found: {entry_id}")

    return _parse_metadata_response(result)


@router.put("/metadata/bulk/update", response_model=BulkUpdateResponse)
async def bulk_update_metadata(data: list[MetadataBulkUpdateItem]) -> BulkUpdateResponse:
    """Bulk update metadata entries."""
    vector_store = get_vector_store_service()

    updated = 0
    not_found: list[str] = []
    errors: list[str] = []

    for item in data:
        try:
            result = vector_store.update_metadata(
                entry_id=item.id,
                title=item.title,
                content=item.content,
                category=item.category.value if item.category else None,
                related_tables=item.related_tables,
                keywords=item.keywords,
            )
            if result:
                updated += 1
            else:
                not_found.append(item.id)
        except Exception as e:
            errors.append(f"Failed to update metadata '{item.id}': {e}")

    return BulkUpdateResponse(updated=updated, not_found=not_found, errors=errors)


@router.delete("/metadata/{entry_id}")
async def delete_metadata(entry_id: str) -> dict:
    """Delete a metadata entry."""
    vector_store = get_vector_store_service()

    if not vector_store.delete_metadata(entry_id):
        raise HTTPException(status_code=404, detail=f"Metadata entry not found: {entry_id}")

    return {"status": "deleted", "id": entry_id}


@router.delete("/metadata/bulk/delete", response_model=BulkDeleteResponse)
async def bulk_delete_metadata(data: BulkDeleteRequest) -> BulkDeleteResponse:
    """Bulk delete metadata entries."""
    vector_store = get_vector_store_service()

    deleted, not_found = vector_store.delete_metadata_bulk(data.ids)

    return BulkDeleteResponse(deleted=deleted, not_found=not_found)


# ============================================================================
# Database Info Endpoints
# ============================================================================


def _parse_database_info_response(item: dict) -> DatabaseInfoResponse:
    """Parse database info item to response model."""
    meta = item["metadata"]
    created_at_str = meta.get("created_at")

    # Parse columns from JSON string
    columns_json = meta.get("columns_json", "[]")
    try:
        columns_data = json.loads(columns_json) if columns_json else []
    except json.JSONDecodeError:
        columns_data = []

    # Parse relationships from JSON string
    relationships_json = meta.get("relationships_json", "[]")
    try:
        relationships_data = json.loads(relationships_json) if relationships_json else []
    except json.JSONDecodeError:
        relationships_data = []

    # Parse row_count (-1 means None)
    row_count = meta.get("row_count")
    if row_count == -1:
        row_count = None

    return DatabaseInfoResponse(
        id=meta["id"],
        schema_name=meta["schema_name"],
        table_name=meta["table_name"],
        full_name=meta["full_name"],
        columns=[
            ColumnInfoResponse(
                name=col.get("name", ""),
                data_type=col.get("data_type", "unknown"),
                is_nullable=col.get("is_nullable", True),
                is_primary_key=col.get("is_primary_key", False),
                is_foreign_key=col.get("is_foreign_key", False),
                foreign_key_table=col.get("foreign_key_table"),
                foreign_key_column=col.get("foreign_key_column"),
                default_value=col.get("default_value"),
                description=col.get("description"),
            )
            for col in columns_data
        ],
        relationships=[
            RelationshipResponse(
                from_table=rel.get("from_table", ""),
                from_column=rel.get("from_column", ""),
                to_table=rel.get("to_table", ""),
                to_column=rel.get("to_column", ""),
                relationship_type=rel.get("relationship_type", "many-to-one"),
            )
            for rel in relationships_data
        ],
        description=meta.get("description") or None,
        row_count=row_count,
        created_at=datetime.fromisoformat(created_at_str) if created_at_str else None,
    )


@router.get("/database-info", response_model=DatabaseInfoListResponse)
async def list_database_info(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> DatabaseInfoListResponse:
    """List all database info entries with pagination."""
    vector_store = get_vector_store_service()
    offset = (page - 1) * page_size

    items = vector_store.list_database_info(limit=page_size, offset=offset)
    total = vector_store.get_database_info_count()

    return DatabaseInfoListResponse(
        items=[_parse_database_info_response(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(offset + page_size) < total,
        has_prev=page > 1,
    )


@router.get("/database-info/{table_id}", response_model=DatabaseInfoResponse)
async def get_database_info(table_id: str) -> DatabaseInfoResponse:
    """Get a single database info entry by ID."""
    vector_store = get_vector_store_service()
    item = vector_store.get_table_info(table_id)

    if not item:
        raise HTTPException(status_code=404, detail=f"Database info not found: {table_id}")

    return _parse_database_info_response(item)


@router.post("/database-info", response_model=DatabaseInfoResponse, status_code=201)
async def create_database_info(data: DatabaseInfoCreate) -> DatabaseInfoResponse:
    """Create a new database info entry."""
    vector_store = get_vector_store_service()

    columns = [
        ColumnInfo(
            name=col.name,
            data_type=col.data_type,
            is_nullable=col.is_nullable,
            is_primary_key=col.is_primary_key,
            is_foreign_key=col.is_foreign_key,
            foreign_key_table=col.foreign_key_table,
            foreign_key_column=col.foreign_key_column,
            default_value=col.default_value,
            description=col.description,
        )
        for col in data.columns
    ]

    relationships = [
        Relationship(
            from_table=rel.from_table,
            from_column=rel.from_column,
            to_table=rel.to_table,
            to_column=rel.to_column,
            relationship_type=rel.relationship_type,
        )
        for rel in data.relationships
    ]

    table = TableInfo(
        schema_name=data.schema_name,
        table_name=data.table_name,
        columns=columns,
        relationships=relationships,
        description=data.description,
        row_count=data.row_count,
    )
    table_id, _ = vector_store.add_table_info(table)

    return DatabaseInfoResponse(
        id=table_id,
        schema_name=data.schema_name,
        table_name=data.table_name,
        full_name=f"{data.schema_name}.{data.table_name}",
        columns=[
            ColumnInfoResponse(
                name=col.name,
                data_type=col.data_type,
                is_nullable=col.is_nullable,
                is_primary_key=col.is_primary_key,
                is_foreign_key=col.is_foreign_key,
                foreign_key_table=col.foreign_key_table,
                foreign_key_column=col.foreign_key_column,
                default_value=col.default_value,
                description=col.description,
            )
            for col in columns
        ],
        relationships=[
            RelationshipResponse(
                from_table=rel.from_table,
                from_column=rel.from_column,
                to_table=rel.to_table,
                to_column=rel.to_column,
                relationship_type=rel.relationship_type,
            )
            for rel in relationships
        ],
        description=data.description,
        row_count=data.row_count,
        created_at=table.created_at,
    )


@router.post("/database-info/bulk", response_model=BulkCreateResponse)
async def bulk_create_database_info(data: list[DatabaseInfoCreate]) -> BulkCreateResponse:
    """Bulk create database info entries."""
    vector_store = get_vector_store_service()

    created = 0
    updated = 0
    failed = 0
    errors: list[str] = []

    for item in data:
        try:
            columns = [
                ColumnInfo(
                    name=col.name,
                    data_type=col.data_type,
                    is_nullable=col.is_nullable,
                    is_primary_key=col.is_primary_key,
                    is_foreign_key=col.is_foreign_key,
                    foreign_key_table=col.foreign_key_table,
                    foreign_key_column=col.foreign_key_column,
                    default_value=col.default_value,
                    description=col.description,
                )
                for col in item.columns
            ]

            relationships = [
                Relationship(
                    from_table=rel.from_table,
                    from_column=rel.from_column,
                    to_table=rel.to_table,
                    to_column=rel.to_column,
                    relationship_type=rel.relationship_type,
                )
                for rel in item.relationships
            ]

            table = TableInfo(
                schema_name=item.schema_name,
                table_name=item.table_name,
                columns=columns,
                relationships=relationships,
                description=item.description,
                row_count=item.row_count,
            )
            _, is_update = vector_store.add_table_info(table)
            if is_update:
                updated += 1
            else:
                created += 1
        except Exception as e:
            failed += 1
            errors.append(f"Failed to create database info '{item.table_name}': {e}")

    return BulkCreateResponse(created=created, updated=updated, failed=failed, errors=errors)


@router.put("/database-info/{table_id}", response_model=DatabaseInfoResponse)
async def update_database_info(table_id: str, data: DatabaseInfoUpdate) -> DatabaseInfoResponse:
    """Update a database info entry."""
    vector_store = get_vector_store_service()

    columns_data = None
    if data.columns is not None:
        columns_data = [col.model_dump() for col in data.columns]

    relationships_data = None
    if data.relationships is not None:
        relationships_data = [rel.model_dump() for rel in data.relationships]

    result = vector_store.update_table_info(
        table_id=table_id,
        schema_name=data.schema_name,
        table_name=data.table_name,
        columns=columns_data,
        relationships=relationships_data,
        description=data.description,
        row_count=data.row_count,
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"Database info not found: {table_id}")

    return _parse_database_info_response(result)


@router.put("/database-info/bulk/update", response_model=BulkUpdateResponse)
async def bulk_update_database_info(data: list[DatabaseInfoBulkUpdateItem]) -> BulkUpdateResponse:
    """Bulk update database info entries."""
    vector_store = get_vector_store_service()

    updated = 0
    not_found: list[str] = []
    errors: list[str] = []

    for item in data:
        try:
            columns_data = None
            if item.columns is not None:
                columns_data = [col.model_dump() for col in item.columns]

            relationships_data = None
            if item.relationships is not None:
                relationships_data = [rel.model_dump() for rel in item.relationships]

            result = vector_store.update_table_info(
                table_id=item.id,
                schema_name=item.schema_name,
                table_name=item.table_name,
                columns=columns_data,
                relationships=relationships_data,
                description=item.description,
                row_count=item.row_count,
            )
            if result:
                updated += 1
            else:
                not_found.append(item.id)
        except Exception as e:
            errors.append(f"Failed to update database info '{item.id}': {e}")

    return BulkUpdateResponse(updated=updated, not_found=not_found, errors=errors)


@router.delete("/database-info/{table_id}")
async def delete_database_info(table_id: str) -> dict:
    """Delete a database info entry."""
    vector_store = get_vector_store_service()

    if not vector_store.delete_table_info(table_id):
        raise HTTPException(status_code=404, detail=f"Database info not found: {table_id}")

    return {"status": "deleted", "id": table_id}


@router.delete("/database-info/bulk/delete", response_model=BulkDeleteResponse)
async def bulk_delete_database_info(data: BulkDeleteRequest) -> BulkDeleteResponse:
    """Bulk delete database info entries."""
    vector_store = get_vector_store_service()

    deleted, not_found = vector_store.delete_table_info_bulk(data.ids)

    return BulkDeleteResponse(deleted=deleted, not_found=not_found)


# ============================================================================
# DDL Import Endpoint
# ============================================================================


@router.post("/database-info/import-ddl", response_model=DDLImportResponse)
async def import_ddl(data: DDLImportRequest) -> DDLImportResponse:
    """Import database schema from DDL (CREATE TABLE) statements.

    Supports TypeORM and standard PostgreSQL CREATE TABLE syntax.
    Extracts table names, column definitions (with types, nullability, defaults),
    and primary key constraints.
    """
    from text_to_sql.utils.ddl_parser import parse_ddl

    vector_store = get_vector_store_service()

    tables_imported = 0
    table_names: list[str] = []
    errors: list[str] = []

    try:
        parsed_tables = parse_ddl(data.ddl, data.schema_name)
    except Exception as e:
        return DDLImportResponse(
            tables_imported=0,
            tables=[],
            errors=[f"Failed to parse DDL: {e}"],
        )

    for parsed in parsed_tables:
        try:
            columns = [
                ColumnInfo(
                    name=col.name,
                    data_type=col.data_type,
                    is_nullable=col.is_nullable,
                    is_primary_key=col.is_primary_key,
                    is_foreign_key=col.is_foreign_key,
                    foreign_key_table=col.foreign_key_table,
                    foreign_key_column=col.foreign_key_column,
                    default_value=col.default_value,
                    description=col.description,
                )
                for col in parsed.columns
            ]

            # Convert foreign keys to relationships
            relationships = [
                Relationship(
                    from_table=parsed.table_name,
                    from_column=fk.from_column,
                    to_table=fk.to_table,
                    to_column=fk.to_column,
                    relationship_type="many-to-one",
                )
                for fk in parsed.foreign_keys
            ]

            table = TableInfo(
                schema_name=parsed.schema_name,
                table_name=parsed.table_name,
                columns=columns,
                relationships=relationships,
                description=parsed.description,
            )

            vector_store.add_table_info(table)
            tables_imported += 1
            table_names.append(f"{parsed.schema_name}.{parsed.table_name}")

        except Exception as e:
            errors.append(f"Failed to import {parsed.schema_name}.{parsed.table_name}: {e}")

    return DDLImportResponse(
        tables_imported=tables_imported,
        tables=table_names,
        errors=errors,
    )
