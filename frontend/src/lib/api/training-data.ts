/**
 * API client for training data candidate review
 */

import type {
  BulkActionRequest,
  BulkActionResponse,
  CandidateCountsResponse,
  CandidateEditRequest,
  CandidateListResponse,
  CandidateStatus,
  SQLPairCandidate,
} from "@/types/training-data";

const API_BASE = "/api/v1/training-data";

export async function listCandidates(
  page: number = 1,
  pageSize: number = 20,
  status?: CandidateStatus
): Promise<CandidateListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) {
    params.set("status", status);
  }
  const response = await fetch(`${API_BASE}/candidates?${params}`);
  if (!response.ok) {
    throw new Error("Failed to list candidates");
  }
  return response.json();
}

export async function updateCandidate(
  id: string,
  data: CandidateEditRequest
): Promise<SQLPairCandidate> {
  const response = await fetch(`${API_BASE}/candidates/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error("Failed to update candidate");
  }
  return response.json();
}

export async function approveCandidate(
  id: string,
  data?: CandidateEditRequest
): Promise<SQLPairCandidate> {
  const response = await fetch(`${API_BASE}/candidates/${id}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data ?? {}),
  });
  if (!response.ok) {
    throw new Error("Failed to approve candidate");
  }
  return response.json();
}

export async function rejectCandidate(
  id: string
): Promise<SQLPairCandidate> {
  const response = await fetch(`${API_BASE}/candidates/${id}/reject`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Failed to reject candidate");
  }
  return response.json();
}

export async function deleteCandidate(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/candidates/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("Failed to delete candidate");
  }
}

export async function bulkApprove(
  ids: string[]
): Promise<BulkActionResponse> {
  const response = await fetch(`${API_BASE}/candidates/bulk-approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids } as BulkActionRequest),
  });
  if (!response.ok) {
    throw new Error("Failed to bulk approve candidates");
  }
  return response.json();
}

export async function bulkReject(
  ids: string[]
): Promise<BulkActionResponse> {
  const response = await fetch(`${API_BASE}/candidates/bulk-reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids } as BulkActionRequest),
  });
  if (!response.ok) {
    throw new Error("Failed to bulk reject candidates");
  }
  return response.json();
}

export async function getCandidateCounts(): Promise<CandidateCountsResponse> {
  const response = await fetch(`${API_BASE}/candidates/counts`);
  if (!response.ok) {
    throw new Error("Failed to get candidate counts");
  }
  return response.json();
}
