/**
 * TypeScript types for training data candidate review API
 */

export type CandidateStatus = "pending" | "approved" | "rejected";

export interface SQLPairCandidate {
  id: string;
  question: string;
  sql_query: string;
  question_hash: string;
  status: CandidateStatus;
  session_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CandidateListResponse {
  items: SQLPairCandidate[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface CandidateEditRequest {
  question?: string;
  sql_query?: string;
}

export interface BulkActionRequest {
  ids: string[];
}

export interface BulkActionResponse {
  success_count: number;
  error_count: number;
  errors: string[];
}

export interface CandidateCountsResponse {
  pending: number;
  approved: number;
  rejected: number;
  total: number;
}
