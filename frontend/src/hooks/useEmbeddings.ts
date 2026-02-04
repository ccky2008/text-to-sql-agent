"use client";

import { useState, useCallback } from "react";
import type {
  SQLPair,
  SQLPairCreate,
  SQLPairUpdate,
  SQLPairListResponse,
  MetadataEntry,
  MetadataCreate,
  MetadataUpdate,
  MetadataListResponse,
  DatabaseInfo,
  DatabaseInfoCreate,
  DatabaseInfoUpdate,
  DatabaseInfoListResponse,
  EmbeddingType,
  BulkCreateResponse,
  BulkDeleteResponse,
  DDLImportResponse,
} from "@/types/embeddings";
import * as api from "@/lib/api/embeddings";

interface UseEmbeddingsState {
  // SQL Pairs
  sqlPairs: SQLPair[];
  sqlPairsTotal: number;
  sqlPairsPage: number;
  sqlPairsHasNext: boolean;
  sqlPairsHasPrev: boolean;

  // Metadata
  metadata: MetadataEntry[];
  metadataTotal: number;
  metadataPage: number;
  metadataHasNext: boolean;
  metadataHasPrev: boolean;

  // Database Info
  databaseInfo: DatabaseInfo[];
  databaseInfoTotal: number;
  databaseInfoPage: number;
  databaseInfoHasNext: boolean;
  databaseInfoHasPrev: boolean;

  // Common state
  loading: boolean;
  error: string | null;
  selectedIds: Set<string>;
  activeTab: EmbeddingType;
}

interface UseEmbeddingsReturn extends UseEmbeddingsState {
  // Tab management
  setActiveTab: (tab: EmbeddingType) => void;

  // Selection
  toggleSelection: (id: string) => void;
  selectAll: () => void;
  clearSelection: () => void;

  // SQL Pairs operations
  loadSQLPairs: (page?: number) => Promise<void>;
  createSQLPair: (data: SQLPairCreate) => Promise<SQLPair>;
  updateSQLPair: (id: string, data: SQLPairUpdate) => Promise<SQLPair>;
  deleteSQLPair: (id: string) => Promise<void>;
  bulkCreateSQLPairs: (data: SQLPairCreate[]) => Promise<BulkCreateResponse>;
  bulkDeleteSQLPairs: (ids: string[]) => Promise<BulkDeleteResponse>;

  // Metadata operations
  loadMetadata: (page?: number) => Promise<void>;
  createMetadata: (data: MetadataCreate) => Promise<MetadataEntry>;
  updateMetadata: (id: string, data: MetadataUpdate) => Promise<MetadataEntry>;
  deleteMetadata: (id: string) => Promise<void>;
  bulkCreateMetadata: (data: MetadataCreate[]) => Promise<BulkCreateResponse>;
  bulkDeleteMetadata: (ids: string[]) => Promise<BulkDeleteResponse>;

  // Database Info operations
  loadDatabaseInfo: (page?: number) => Promise<void>;
  createDatabaseInfo: (data: DatabaseInfoCreate) => Promise<DatabaseInfo>;
  updateDatabaseInfo: (
    id: string,
    data: DatabaseInfoUpdate
  ) => Promise<DatabaseInfo>;
  deleteDatabaseInfo: (id: string) => Promise<void>;
  bulkCreateDatabaseInfo: (
    data: DatabaseInfoCreate[]
  ) => Promise<BulkCreateResponse>;
  bulkDeleteDatabaseInfo: (ids: string[]) => Promise<BulkDeleteResponse>;
  importDDL: (ddl: string, schemaName: string) => Promise<DDLImportResponse>;

  // Generic operations
  refreshCurrentTab: () => Promise<void>;
  deleteSelected: () => Promise<BulkDeleteResponse>;
}

const PAGE_SIZE = 20;

export function useEmbeddings(): UseEmbeddingsReturn {
  const [state, setState] = useState<UseEmbeddingsState>({
    // SQL Pairs
    sqlPairs: [],
    sqlPairsTotal: 0,
    sqlPairsPage: 1,
    sqlPairsHasNext: false,
    sqlPairsHasPrev: false,

    // Metadata
    metadata: [],
    metadataTotal: 0,
    metadataPage: 1,
    metadataHasNext: false,
    metadataHasPrev: false,

    // Database Info
    databaseInfo: [],
    databaseInfoTotal: 0,
    databaseInfoPage: 1,
    databaseInfoHasNext: false,
    databaseInfoHasPrev: false,

    // Common
    loading: false,
    error: null,
    selectedIds: new Set(),
    activeTab: "sql-pairs",
  });

  // Tab management
  const setActiveTab = useCallback((tab: EmbeddingType) => {
    setState((prev) => ({ ...prev, activeTab: tab, selectedIds: new Set() }));
  }, []);

  // Selection management
  const toggleSelection = useCallback((id: string) => {
    setState((prev) => {
      const newSelected = new Set(prev.selectedIds);
      if (newSelected.has(id)) {
        newSelected.delete(id);
      } else {
        newSelected.add(id);
      }
      return { ...prev, selectedIds: newSelected };
    });
  }, []);

  const selectAll = useCallback(() => {
    setState((prev) => {
      let ids: string[];
      switch (prev.activeTab) {
        case "sql-pairs":
          ids = prev.sqlPairs.map((p) => p.id);
          break;
        case "metadata":
          ids = prev.metadata.map((m) => m.id);
          break;
        case "database-info":
          ids = prev.databaseInfo.map((d) => d.id);
          break;
      }
      return { ...prev, selectedIds: new Set(ids) };
    });
  }, []);

  const clearSelection = useCallback(() => {
    setState((prev) => ({ ...prev, selectedIds: new Set() }));
  }, []);

  // SQL Pairs operations
  const loadSQLPairs = useCallback(async (page: number = 1) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response: SQLPairListResponse = await api.listSQLPairs(
        page,
        PAGE_SIZE
      );
      setState((prev) => ({
        ...prev,
        sqlPairs: response.items,
        sqlPairsTotal: response.total,
        sqlPairsPage: response.page,
        sqlPairsHasNext: response.has_next,
        sqlPairsHasPrev: response.has_prev,
        loading: false,
      }));
    } catch (e) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: e instanceof Error ? e.message : "Failed to load SQL pairs",
      }));
    }
  }, []);

  const createSQLPair = useCallback(
    async (data: SQLPairCreate): Promise<SQLPair> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.createSQLPair(data);
        await loadSQLPairs(state.sqlPairsPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: e instanceof Error ? e.message : "Failed to create SQL pair",
        }));
        throw e;
      }
    },
    [loadSQLPairs, state.sqlPairsPage]
  );

  const updateSQLPair = useCallback(
    async (id: string, data: SQLPairUpdate): Promise<SQLPair> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.updateSQLPair(id, data);
        await loadSQLPairs(state.sqlPairsPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: e instanceof Error ? e.message : "Failed to update SQL pair",
        }));
        throw e;
      }
    },
    [loadSQLPairs, state.sqlPairsPage]
  );

  const deleteSQLPair = useCallback(
    async (id: string): Promise<void> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        await api.deleteSQLPair(id);
        await loadSQLPairs(state.sqlPairsPage);
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: e instanceof Error ? e.message : "Failed to delete SQL pair",
        }));
        throw e;
      }
    },
    [loadSQLPairs, state.sqlPairsPage]
  );

  const bulkCreateSQLPairs = useCallback(
    async (data: SQLPairCreate[]): Promise<BulkCreateResponse> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.bulkCreateSQLPairs(data);
        await loadSQLPairs(state.sqlPairsPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            e instanceof Error ? e.message : "Failed to bulk create SQL pairs",
        }));
        throw e;
      }
    },
    [loadSQLPairs, state.sqlPairsPage]
  );

  const bulkDeleteSQLPairs = useCallback(
    async (ids: string[]): Promise<BulkDeleteResponse> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.bulkDeleteSQLPairs(ids);
        setState((prev) => ({ ...prev, selectedIds: new Set() }));
        await loadSQLPairs(state.sqlPairsPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            e instanceof Error ? e.message : "Failed to bulk delete SQL pairs",
        }));
        throw e;
      }
    },
    [loadSQLPairs, state.sqlPairsPage]
  );

  // Metadata operations
  const loadMetadata = useCallback(async (page: number = 1) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response: MetadataListResponse = await api.listMetadata(
        page,
        PAGE_SIZE
      );
      setState((prev) => ({
        ...prev,
        metadata: response.items,
        metadataTotal: response.total,
        metadataPage: response.page,
        metadataHasNext: response.has_next,
        metadataHasPrev: response.has_prev,
        loading: false,
      }));
    } catch (e) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: e instanceof Error ? e.message : "Failed to load metadata",
      }));
    }
  }, []);

  const createMetadata = useCallback(
    async (data: MetadataCreate): Promise<MetadataEntry> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.createMetadata(data);
        await loadMetadata(state.metadataPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: e instanceof Error ? e.message : "Failed to create metadata",
        }));
        throw e;
      }
    },
    [loadMetadata, state.metadataPage]
  );

  const updateMetadata = useCallback(
    async (id: string, data: MetadataUpdate): Promise<MetadataEntry> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.updateMetadata(id, data);
        await loadMetadata(state.metadataPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: e instanceof Error ? e.message : "Failed to update metadata",
        }));
        throw e;
      }
    },
    [loadMetadata, state.metadataPage]
  );

  const deleteMetadata = useCallback(
    async (id: string): Promise<void> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        await api.deleteMetadata(id);
        await loadMetadata(state.metadataPage);
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: e instanceof Error ? e.message : "Failed to delete metadata",
        }));
        throw e;
      }
    },
    [loadMetadata, state.metadataPage]
  );

  const bulkCreateMetadata = useCallback(
    async (data: MetadataCreate[]): Promise<BulkCreateResponse> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.bulkCreateMetadata(data);
        await loadMetadata(state.metadataPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            e instanceof Error ? e.message : "Failed to bulk create metadata",
        }));
        throw e;
      }
    },
    [loadMetadata, state.metadataPage]
  );

  const bulkDeleteMetadata = useCallback(
    async (ids: string[]): Promise<BulkDeleteResponse> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.bulkDeleteMetadata(ids);
        setState((prev) => ({ ...prev, selectedIds: new Set() }));
        await loadMetadata(state.metadataPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            e instanceof Error ? e.message : "Failed to bulk delete metadata",
        }));
        throw e;
      }
    },
    [loadMetadata, state.metadataPage]
  );

  // Database Info operations
  const loadDatabaseInfo = useCallback(async (page: number = 1) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response: DatabaseInfoListResponse = await api.listDatabaseInfo(
        page,
        PAGE_SIZE
      );
      setState((prev) => ({
        ...prev,
        databaseInfo: response.items,
        databaseInfoTotal: response.total,
        databaseInfoPage: response.page,
        databaseInfoHasNext: response.has_next,
        databaseInfoHasPrev: response.has_prev,
        loading: false,
      }));
    } catch (e) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: e instanceof Error ? e.message : "Failed to load database info",
      }));
    }
  }, []);

  const createDatabaseInfo = useCallback(
    async (data: DatabaseInfoCreate): Promise<DatabaseInfo> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.createDatabaseInfo(data);
        await loadDatabaseInfo(state.databaseInfoPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            e instanceof Error ? e.message : "Failed to create database info",
        }));
        throw e;
      }
    },
    [loadDatabaseInfo, state.databaseInfoPage]
  );

  const updateDatabaseInfo = useCallback(
    async (id: string, data: DatabaseInfoUpdate): Promise<DatabaseInfo> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.updateDatabaseInfo(id, data);
        await loadDatabaseInfo(state.databaseInfoPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            e instanceof Error ? e.message : "Failed to update database info",
        }));
        throw e;
      }
    },
    [loadDatabaseInfo, state.databaseInfoPage]
  );

  const deleteDatabaseInfo = useCallback(
    async (id: string): Promise<void> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        await api.deleteDatabaseInfo(id);
        await loadDatabaseInfo(state.databaseInfoPage);
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            e instanceof Error ? e.message : "Failed to delete database info",
        }));
        throw e;
      }
    },
    [loadDatabaseInfo, state.databaseInfoPage]
  );

  const bulkCreateDatabaseInfo = useCallback(
    async (data: DatabaseInfoCreate[]): Promise<BulkCreateResponse> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.bulkCreateDatabaseInfo(data);
        await loadDatabaseInfo(state.databaseInfoPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            e instanceof Error
              ? e.message
              : "Failed to bulk create database info",
        }));
        throw e;
      }
    },
    [loadDatabaseInfo, state.databaseInfoPage]
  );

  const bulkDeleteDatabaseInfo = useCallback(
    async (ids: string[]): Promise<BulkDeleteResponse> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.bulkDeleteDatabaseInfo(ids);
        setState((prev) => ({ ...prev, selectedIds: new Set() }));
        await loadDatabaseInfo(state.databaseInfoPage);
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error:
            e instanceof Error
              ? e.message
              : "Failed to bulk delete database info",
        }));
        throw e;
      }
    },
    [loadDatabaseInfo, state.databaseInfoPage]
  );

  const importDDL = useCallback(
    async (ddl: string, schemaName: string): Promise<DDLImportResponse> => {
      setState((prev) => ({ ...prev, loading: true, error: null }));
      try {
        const result = await api.importDDL(ddl, schemaName);
        await loadDatabaseInfo(state.databaseInfoPage);
        setState((prev) => ({ ...prev, loading: false }));
        return result;
      } catch (e) {
        setState((prev) => ({
          ...prev,
          loading: false,
          error: e instanceof Error ? e.message : "Failed to import DDL",
        }));
        throw e;
      }
    },
    [loadDatabaseInfo, state.databaseInfoPage]
  );

  // Generic operations
  const refreshCurrentTab = useCallback(async () => {
    switch (state.activeTab) {
      case "sql-pairs":
        await loadSQLPairs(state.sqlPairsPage);
        break;
      case "metadata":
        await loadMetadata(state.metadataPage);
        break;
      case "database-info":
        await loadDatabaseInfo(state.databaseInfoPage);
        break;
    }
  }, [
    state.activeTab,
    state.sqlPairsPage,
    state.metadataPage,
    state.databaseInfoPage,
    loadSQLPairs,
    loadMetadata,
    loadDatabaseInfo,
  ]);

  const deleteSelected = useCallback(async (): Promise<BulkDeleteResponse> => {
    const ids = Array.from(state.selectedIds);
    if (ids.length === 0) {
      return { deleted: 0, not_found: [] };
    }

    switch (state.activeTab) {
      case "sql-pairs":
        return bulkDeleteSQLPairs(ids);
      case "metadata":
        return bulkDeleteMetadata(ids);
      case "database-info":
        return bulkDeleteDatabaseInfo(ids);
    }
  }, [
    state.activeTab,
    state.selectedIds,
    bulkDeleteSQLPairs,
    bulkDeleteMetadata,
    bulkDeleteDatabaseInfo,
  ]);

  return {
    ...state,

    // Tab management
    setActiveTab,

    // Selection
    toggleSelection,
    selectAll,
    clearSelection,

    // SQL Pairs
    loadSQLPairs,
    createSQLPair,
    updateSQLPair,
    deleteSQLPair,
    bulkCreateSQLPairs,
    bulkDeleteSQLPairs,

    // Metadata
    loadMetadata,
    createMetadata,
    updateMetadata,
    deleteMetadata,
    bulkCreateMetadata,
    bulkDeleteMetadata,

    // Database Info
    loadDatabaseInfo,
    createDatabaseInfo,
    updateDatabaseInfo,
    deleteDatabaseInfo,
    bulkCreateDatabaseInfo,
    bulkDeleteDatabaseInfo,
    importDDL,

    // Generic
    refreshCurrentTab,
    deleteSelected,
  };
}
