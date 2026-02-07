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
  | "step_started"
  | "step_completed"
  | "retrieval_complete"
  | "sql_generated"
  | "validation_complete"
  | "execution_complete"
  | "tool_execution_complete"
  | "token"
  | "response_complete"
  | "suggested_questions"
  | "clarification_needed"
  | "error"
  | "done";

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
