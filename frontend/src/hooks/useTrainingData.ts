"use client";

import { useCallback, useEffect, useState } from "react";
import type {
  CandidateCountsResponse,
  CandidateStatus,
  SQLPairCandidate,
} from "@/types/training-data";
import {
  approveCandidate,
  bulkApprove,
  bulkReject,
  deleteCandidate,
  getCandidateCounts,
  listCandidates,
  rejectCandidate,
  updateCandidate,
} from "@/lib/api/training-data";

interface UseTrainingDataState {
  items: SQLPairCandidate[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  hasPrev: boolean;
  statusFilter: CandidateStatus | undefined;
  counts: CandidateCountsResponse;
  selectedIds: Set<string>;
  loading: boolean;
  error: string | null;
}

export function useTrainingData(initialPageSize: number = 20) {
  const [state, setState] = useState<UseTrainingDataState>({
    items: [],
    total: 0,
    page: 1,
    pageSize: initialPageSize,
    hasNext: false,
    hasPrev: false,
    statusFilter: "pending",
    counts: { pending: 0, approved: 0, rejected: 0, total: 0 },
    selectedIds: new Set(),
    loading: true,
    error: null,
  });

  const fetchData = useCallback(async (page: number, pageSize: number, status: CandidateStatus | undefined) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const [listResult, countsResult] = await Promise.all([
        listCandidates(page, pageSize, status),
        getCandidateCounts(),
      ]);
      setState((prev) => ({
        ...prev,
        items: listResult.items,
        total: listResult.total,
        page: listResult.page,
        pageSize: listResult.page_size,
        hasNext: listResult.has_next,
        hasPrev: listResult.has_prev,
        counts: countsResult,
        selectedIds: new Set(),
        loading: false,
      }));
    } catch (e) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: e instanceof Error ? e.message : "Failed to load data",
      }));
    }
  }, []);

  const refresh = useCallback(() => {
    fetchData(state.page, state.pageSize, state.statusFilter);
  }, [fetchData, state.page, state.pageSize, state.statusFilter]);

  useEffect(() => {
    fetchData(state.page, state.pageSize, state.statusFilter);
  }, [fetchData, state.page, state.pageSize, state.statusFilter]);

  const setPage = useCallback((page: number) => {
    setState((prev) => ({ ...prev, page }));
  }, []);

  const setStatusFilter = useCallback((status: CandidateStatus | undefined) => {
    setState((prev) => ({ ...prev, statusFilter: status, page: 1, selectedIds: new Set() }));
  }, []);

  const toggleSelection = useCallback((id: string) => {
    setState((prev) => {
      const next = new Set(prev.selectedIds);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return { ...prev, selectedIds: next };
    });
  }, []);

  const selectAll = useCallback(() => {
    setState((prev) => ({
      ...prev,
      selectedIds: new Set(prev.items.map((item) => item.id)),
    }));
  }, []);

  const clearSelection = useCallback(() => {
    setState((prev) => ({ ...prev, selectedIds: new Set() }));
  }, []);

  const handleApprove = useCallback(
    async (id: string, question?: string, sqlQuery?: string) => {
      await approveCandidate(id, { question, sql_query: sqlQuery });
      refresh();
    },
    [refresh]
  );

  const handleReject = useCallback(
    async (id: string) => {
      await rejectCandidate(id);
      refresh();
    },
    [refresh]
  );

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteCandidate(id);
      refresh();
    },
    [refresh]
  );

  const handleUpdate = useCallback(
    async (id: string, question?: string, sqlQuery?: string) => {
      await updateCandidate(id, { question, sql_query: sqlQuery });
      refresh();
    },
    [refresh]
  );

  const handleBulkApprove = useCallback(async () => {
    const ids = Array.from(state.selectedIds);
    if (ids.length === 0) return;
    await bulkApprove(ids);
    refresh();
  }, [state.selectedIds, refresh]);

  const handleBulkReject = useCallback(async () => {
    const ids = Array.from(state.selectedIds);
    if (ids.length === 0) return;
    await bulkReject(ids);
    refresh();
  }, [state.selectedIds, refresh]);

  return {
    ...state,
    setPage,
    setStatusFilter,
    toggleSelection,
    selectAll,
    clearSelection,
    handleApprove,
    handleReject,
    handleDelete,
    handleUpdate,
    handleBulkApprove,
    handleBulkReject,
    refresh,
  };
}
