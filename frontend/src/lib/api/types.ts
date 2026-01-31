/**
 * API types matching the backend models
 */

// Pagination types
export interface PaginationInfo {
  page: number;
  page_size: number;
  total_count: number | null;
  total_pages: number | null;
  has_next: boolean;
  has_prev: boolean;
}

// Request types
export interface QueryRequest {
  question: string;
  session_id?: string | null;
  execute?: boolean;
  stream?: boolean;
  page?: number;
  page_size?: number;
}

export interface CSVDownloadRequest {
  query_token: string;
  offset?: number;
  limit?: number;
  filename?: string;
}

// Response types
export interface QueryResponse {
  question: string;
  generated_sql: string | null;
  explanation: string | null;
  is_valid: boolean;
  validation_errors: string[];
  validation_warnings: string[];
  executed: boolean;
  results: Record<string, unknown>[] | null;
  row_count: number | null;
  columns: string[] | null;
  natural_language_response: string | null;
  suggested_questions: string[];
  session_id: string;
  error: string | null;
  pagination: PaginationInfo | null;
  csv_available: boolean;
  csv_exceeds_limit: boolean;
  query_token: string | null;
}

export interface CSVLimitsResponse {
  max_rows_per_download: number;
  batch_download_available: boolean;
  batch_download_instructions: string;
}

// Suggested questions types
export interface SuggestedQuestionsResponse {
  questions: string[];
  context_type: "initial" | "follow_up";
}

// SSE Event types
export type SSEEventType =
  | "retrieval_complete"
  | "sql_generated"
  | "validation_complete"
  | "execution_complete"
  | "tool_execution_complete"
  | "token"
  | "response_complete"
  | "suggested_questions"
  | "error"
  | "done";

export interface SSEEvent {
  event: SSEEventType;
  data: Record<string, unknown>;
}

// Specific SSE event data types
export interface RetrievalCompleteData {
  sql_pairs_count: number;
  metadata_count: number;
  database_info_count: number;
}

export interface SQLGeneratedData {
  sql: string;
  explanation: string;
}

export interface ValidationCompleteData {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ExecutionCompleteData {
  executed: boolean;
  row_count: number | null;
  columns: string[] | null;
  results: Record<string, unknown>[] | null;
  total_count: number | null;
  has_more: boolean;
  page: number;
  page_size: number;
  csv_available: boolean;
  csv_exceeds_limit: boolean;
  query_token: string | null;
}

export interface ToolExecutionCompleteData {
  tool_name: string;
  success: boolean;
  rows: Record<string, unknown>[] | null;
  columns: string[] | null;
  row_count: number;
  total_count: number | null;
  has_more: boolean;
  page: number;
  page_size: number;
  query_token: string | null;
  error: string | null;
}

export interface TokenData {
  token: string;
}

export interface ResponseCompleteData {
  response: string;
}

export interface ErrorData {
  error: string;
}

export interface DoneData {
  session_id: string;
}

// Session types
export interface SessionInfo {
  session_id: string;
  created_at: string;
  last_active: string;
  message_count: number;
}

export interface SessionListResponse {
  sessions: SessionInfo[];
  total: number;
}

// Health types
export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  services: Record<string, boolean>;
}
