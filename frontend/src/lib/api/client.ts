/**
 * API client for the Text-to-SQL backend
 */

import type {
  QueryRequest,
  QueryResponse,
  SSEEventType,
  SessionInfo,
  SessionListResponse,
  HealthResponse,
  CSVDownloadRequest,
  CSVLimitsResponse,
  SuggestedQuestionsResponse,
} from "./types";

const API_BASE = "/api/v1";

// For SSE streaming, connect directly to the backend to avoid
// Next.js rewrite proxy buffering which breaks real-time streaming.
const STREAMING_API_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/api/v1";

/**
 * Callback type for handling SSE events
 */
export type SSEEventCallback = (
  event: SSEEventType,
  data: Record<string, unknown>
) => void;

/**
 * Send a query to the backend with SSE streaming
 */
export async function queryWithStreaming(
  request: QueryRequest,
  onEvent: SSEEventCallback,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${STREAMING_API_BASE}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ ...request, stream: true }),
    signal,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Query failed: ${error}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent: SSEEventType | null = null;

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim() as SSEEventType;
        } else if (line.startsWith("data: ") && currentEvent) {
          try {
            const data = JSON.parse(line.slice(6));
            onEvent(currentEvent, data);
          } catch {
            // Skip malformed JSON
          }
          currentEvent = null;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Send a query to the backend without streaming
 */
export async function query(request: QueryRequest): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ ...request, stream: false }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Query failed: ${error}`);
  }

  return response.json();
}

/**
 * List all sessions
 */
export async function listSessions(): Promise<SessionListResponse> {
  const response = await fetch(`${API_BASE}/sessions`);
  if (!response.ok) {
    throw new Error("Failed to list sessions");
  }
  return response.json();
}

/**
 * Get a specific session
 */
export async function getSession(sessionId: string): Promise<SessionInfo> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error("Failed to get session");
  }
  return response.json();
}

/**
 * Delete a session
 */
export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("Failed to delete session");
  }
}

/**
 * Check backend health
 */
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error("Health check failed");
  }
  return response.json();
}

/**
 * Download query results as CSV
 */
export async function downloadCSV(request: CSVDownloadRequest): Promise<void> {
  const response = await fetch(`${API_BASE}/csv`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`CSV download failed: ${error}`);
  }

  // Trigger browser download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = request.filename || "query_results.csv";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

/**
 * Get CSV download limits
 */
export async function getCSVLimits(): Promise<CSVLimitsResponse> {
  const response = await fetch(`${API_BASE}/csv/limits`);
  if (!response.ok) {
    throw new Error("Failed to get CSV limits");
  }
  return response.json();
}

/**
 * Get initial suggested questions for a new chat
 */
export async function getSuggestedQuestions(): Promise<SuggestedQuestionsResponse> {
  const response = await fetch(`${API_BASE}/suggestions/initial`);
  if (!response.ok) {
    throw new Error("Failed to get suggested questions");
  }
  return response.json();
}
