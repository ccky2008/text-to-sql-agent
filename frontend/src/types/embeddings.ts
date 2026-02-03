/**
 * TypeScript types for embeddings management API
 */

// ============================================================================
// SQL Pairs Types
// ============================================================================

export interface SQLPair {
  id: string;
  question: string;
  sql_query: string;
}

export interface SQLPairCreate {
  question: string;
  sql_query: string;
}

export interface SQLPairUpdate {
  question?: string;
  sql_query?: string;
}

export interface SQLPairListResponse {
  items: SQLPair[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

// ============================================================================
// Metadata Types
// ============================================================================

export type MetadataCategory = "business_rule" | "domain_term" | "context";

export interface MetadataEntry {
  id: string;
  title: string;
  content: string;
  category: MetadataCategory;
  related_tables: string[];
  keywords: string[];
  created_at?: string;
}

export interface MetadataCreate {
  title: string;
  content: string;
  category: MetadataCategory;
  related_tables?: string[];
  keywords?: string[];
}

export interface MetadataUpdate {
  title?: string;
  content?: string;
  category?: MetadataCategory;
  related_tables?: string[];
  keywords?: string[];
}

export interface MetadataListResponse {
  items: MetadataEntry[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

// ============================================================================
// Database Info Types
// ============================================================================

export interface ColumnInfo {
  name: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  foreign_key_table?: string | null;
  foreign_key_column?: string | null;
  default_value?: string | null;
  description?: string | null;
}

export interface Relationship {
  from_table: string;
  from_column: string;
  to_table: string;
  to_column: string;
  relationship_type: string;
}

export interface DatabaseInfo {
  id: string;
  schema_name: string;
  table_name: string;
  full_name: string;
  columns: ColumnInfo[];
  relationships: Relationship[];
  description?: string | null;
  row_count?: number | null;
  created_at?: string;
}

export interface DatabaseInfoCreate {
  schema_name?: string;
  table_name: string;
  columns?: ColumnInfo[];
  relationships?: Relationship[];
  description?: string;
  row_count?: number;
}

export interface DatabaseInfoUpdate {
  schema_name?: string;
  table_name?: string;
  columns?: ColumnInfo[];
  relationships?: Relationship[];
  description?: string;
  row_count?: number;
}

export interface DatabaseInfoListResponse {
  items: DatabaseInfo[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

// ============================================================================
// DDL Import Types
// ============================================================================

export interface DDLImportRequest {
  ddl: string;
  schema_name?: string;
}

export interface DDLImportResponse {
  tables_imported: number;
  tables: string[];
  errors: string[];
}

// ============================================================================
// Bulk Operation Types
// ============================================================================

export interface BulkCreateResponse {
  created: number;
  updated: number;
  failed: number;
  errors: string[];
}

export interface BulkDeleteRequest {
  ids: string[];
}

export interface BulkDeleteResponse {
  deleted: number;
  not_found: string[];
}

export interface BulkUpdateResponse {
  updated: number;
  not_found: string[];
  errors: string[];
}

// Bulk update item types
export interface SQLPairBulkUpdateItem {
  id: string;
  question?: string;
  sql_query?: string;
}

export interface MetadataBulkUpdateItem {
  id: string;
  title?: string;
  content?: string;
  category?: MetadataCategory;
  related_tables?: string[];
  keywords?: string[];
}

export interface DatabaseInfoBulkUpdateItem {
  id: string;
  schema_name?: string;
  table_name?: string;
  columns?: ColumnInfo[];
  relationships?: Relationship[];
  description?: string;
  row_count?: number;
}

// ============================================================================
// Generic Types
// ============================================================================

export type EmbeddingType = "sql-pairs" | "metadata" | "database-info";

export type EmbeddingItem = SQLPair | MetadataEntry | DatabaseInfo;

export type EmbeddingListResponse =
  | SQLPairListResponse
  | MetadataListResponse
  | DatabaseInfoListResponse;
