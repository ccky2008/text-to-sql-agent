/**
 * Chat-specific types for the frontend
 */

export type MessageRole = "user" | "assistant";

export interface SQLResult {
  sql: string;
  explanation: string | null;
  isValid: boolean;
  validationErrors: string[];
  validationWarnings: string[];
  executed: boolean;
  results: Record<string, unknown>[] | null;
  rowCount: number | null;
  columns: string[] | null;
  // Pagination fields
  totalCount: number | null;
  hasMore: boolean;
  page: number;
  pageSize: number;
  // CSV fields
  csvAvailable: boolean;
  csvExceedsLimit: boolean;
  queryToken: string | null;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  sqlResult?: SQLResult;
  isStreaming?: boolean;
  error?: string;
}

export interface ChatState {
  messages: Message[];
  sessionId: string | null;
  isLoading: boolean;
  error: string | null;
}
