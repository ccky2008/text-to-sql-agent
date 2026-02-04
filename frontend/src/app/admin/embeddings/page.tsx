"use client";

import { useEffect, useState, useCallback } from "react";
import { useEmbeddings } from "@/hooks/useEmbeddings";
import {
  DataTable,
  Pagination,
  ConfirmDialog,
  BulkImportModal,
  SQLPairForm,
  MetadataForm,
  DatabaseInfoForm,
} from "@/components/admin";
import type {
  EmbeddingType,
  SQLPair,
  MetadataEntry,
  DatabaseInfo,
  SQLPairCreate,
  SQLPairUpdate,
  MetadataCreate,
  MetadataUpdate,
  DatabaseInfoCreate,
  DatabaseInfoUpdate,
} from "@/types/embeddings";

const TABS: { id: EmbeddingType; label: string }[] = [
  { id: "sql-pairs", label: "SQL Pairs" },
  { id: "metadata", label: "Metadata" },
  { id: "database-info", label: "Database Info" },
];

export default function EmbeddingsPage() {
  const {
    // State
    activeTab,
    loading,
    error,
    selectedIds,
    // SQL Pairs
    sqlPairs,
    sqlPairsTotal,
    sqlPairsPage,
    sqlPairsHasNext,
    sqlPairsHasPrev,
    // Metadata
    metadata,
    metadataTotal,
    metadataPage,
    metadataHasNext,
    metadataHasPrev,
    // Database Info
    databaseInfo,
    databaseInfoTotal,
    databaseInfoPage,
    databaseInfoHasNext,
    databaseInfoHasPrev,
    // Actions
    setActiveTab,
    toggleSelection,
    selectAll,
    clearSelection,
    loadSQLPairs,
    createSQLPair,
    updateSQLPair,
    deleteSQLPair,
    bulkCreateSQLPairs,
    loadMetadata,
    createMetadata,
    updateMetadata,
    deleteMetadata,
    bulkCreateMetadata,
    loadDatabaseInfo,
    createDatabaseInfo,
    updateDatabaseInfo,
    deleteDatabaseInfo,
    bulkCreateDatabaseInfo,
    importDDL,
    deleteSelected,
  } = useEmbeddings();

  // Modal states
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState<SQLPair | MetadataEntry | DatabaseInfo | null>(null);
  const [showImport, setShowImport] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<SQLPair | MetadataEntry | DatabaseInfo | null>(null);
  const [showBulkDeleteConfirm, setShowBulkDeleteConfirm] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Load data on mount and tab change
  useEffect(() => {
    switch (activeTab) {
      case "sql-pairs":
        loadSQLPairs();
        break;
      case "metadata":
        loadMetadata();
        break;
      case "database-info":
        loadDatabaseInfo();
        break;
    }
  }, [activeTab, loadSQLPairs, loadMetadata, loadDatabaseInfo]);

  // Auto-hide notification
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  const showNotification = useCallback((type: "success" | "error", message: string) => {
    setNotification({ type, message });
  }, []);

  // Handlers
  const handlePageChange = (page: number) => {
    switch (activeTab) {
      case "sql-pairs":
        loadSQLPairs(page);
        break;
      case "metadata":
        loadMetadata(page);
        break;
      case "database-info":
        loadDatabaseInfo(page);
        break;
    }
  };

  const handleAdd = () => {
    setEditItem(null);
    setShowForm(true);
  };

  const handleEdit = (item: SQLPair | MetadataEntry | DatabaseInfo) => {
    setEditItem(item);
    setShowForm(true);
  };

  const handleDelete = (item: SQLPair | MetadataEntry | DatabaseInfo) => {
    setDeleteTarget(item);
    setShowDeleteConfirm(true);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;

    try {
      switch (activeTab) {
        case "sql-pairs":
          await deleteSQLPair(deleteTarget.id);
          break;
        case "metadata":
          await deleteMetadata(deleteTarget.id);
          break;
        case "database-info":
          await deleteDatabaseInfo(deleteTarget.id);
          break;
      }
      showNotification("success", "Item deleted successfully");
    } catch {
      showNotification("error", "Failed to delete item");
    } finally {
      setShowDeleteConfirm(false);
      setDeleteTarget(null);
    }
  };

  const handleBulkDelete = () => {
    if (selectedIds.size === 0) return;
    setShowBulkDeleteConfirm(true);
  };

  const confirmBulkDelete = async () => {
    try {
      const result = await deleteSelected();
      showNotification("success", `Deleted ${result.deleted} items`);
    } catch {
      showNotification("error", "Failed to delete items");
    } finally {
      setShowBulkDeleteConfirm(false);
    }
  };

  const handleSave = async (data: SQLPairCreate | SQLPairUpdate | MetadataCreate | MetadataUpdate | DatabaseInfoCreate | DatabaseInfoUpdate) => {
    try {
      switch (activeTab) {
        case "sql-pairs":
          if (editItem) {
            await updateSQLPair(editItem.id, data as SQLPairUpdate);
          } else {
            await createSQLPair(data as SQLPairCreate);
          }
          break;
        case "metadata":
          if (editItem) {
            await updateMetadata(editItem.id, data as MetadataUpdate);
          } else {
            await createMetadata(data as MetadataCreate);
          }
          break;
        case "database-info":
          if (editItem) {
            await updateDatabaseInfo(editItem.id, data as DatabaseInfoUpdate);
          } else {
            await createDatabaseInfo(data as DatabaseInfoCreate);
          }
          break;
      }
      showNotification("success", editItem ? "Item updated" : "Item created");
    } catch {
      throw new Error("Failed to save");
    }
  };

  const handleImport = async (data: unknown[]) => {
    try {
      let result;
      switch (activeTab) {
        case "sql-pairs":
          result = await bulkCreateSQLPairs(data as SQLPairCreate[]);
          break;
        case "metadata":
          result = await bulkCreateMetadata(data as MetadataCreate[]);
          break;
        case "database-info":
          result = await bulkCreateDatabaseInfo(data as DatabaseInfoCreate[]);
          break;
      }
      showNotification(
        "success",
        `Created ${result.created}, updated ${result.updated}, failed ${result.failed}`
      );
    } catch {
      throw new Error("Import failed");
    }
  };

  // Current tab data computed from active tab
  function getCurrentTabData() {
    switch (activeTab) {
      case "sql-pairs":
        return {
          items: sqlPairs,
          total: sqlPairsTotal,
          page: sqlPairsPage,
          hasNext: sqlPairsHasNext,
          hasPrev: sqlPairsHasPrev,
        };
      case "metadata":
        return {
          items: metadata,
          total: metadataTotal,
          page: metadataPage,
          hasNext: metadataHasNext,
          hasPrev: metadataHasPrev,
        };
      case "database-info":
        return {
          items: databaseInfo,
          total: databaseInfoTotal,
          page: databaseInfoPage,
          hasNext: databaseInfoHasNext,
          hasPrev: databaseInfoHasPrev,
        };
    }
  }

  const currentTabData = getCurrentTabData();

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Embeddings Management
        </h2>
        <p className="text-gray-600 dark:text-gray-400">
          Manage SQL pairs, metadata, and database schema information for the text-to-SQL agent.
        </p>
      </div>

      {/* Notification */}
      {notification && (
        <div
          className={`mb-4 px-4 py-3 rounded-md text-sm ${
            notification.type === "success"
              ? "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400"
              : "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400"
          }`}
        >
          {notification.message}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 rounded-md text-sm bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 mb-4">
        <nav className="flex gap-4">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? "border-blue-500 text-blue-600 dark:text-blue-400"
                  : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              }`}
            >
              {tab.label}
              <span className="ml-2 text-xs text-gray-400">
                ({activeTab === tab.id ? currentTabData.total : "..."})
              </span>
            </button>
          ))}
        </nav>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={handleAdd}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
          >
            + Add New
          </button>
          <button
            onClick={() => setShowImport(true)}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
          >
            Import JSON
          </button>
          {selectedIds.size > 0 && (
            <button
              onClick={handleBulkDelete}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors"
            >
              Delete Selected ({selectedIds.size})
            </button>
          )}
        </div>
        {loading && (
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Loading...
          </span>
        )}
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <DataTable
          items={currentTabData.items}
          selectedIds={selectedIds}
          onToggleSelection={toggleSelection}
          onSelectAll={selectAll}
          onClearSelection={clearSelection}
          onEdit={handleEdit}
          onDelete={handleDelete}
          type={activeTab}
        />
        <Pagination
          page={currentTabData.page}
          total={currentTabData.total}
          pageSize={20}
          hasNext={currentTabData.hasNext}
          hasPrev={currentTabData.hasPrev}
          onPageChange={handlePageChange}
        />
      </div>

      {/* Forms */}
      {activeTab === "sql-pairs" && (
        <SQLPairForm
          isOpen={showForm}
          initialData={editItem as SQLPair | null}
          onClose={() => {
            setShowForm(false);
            setEditItem(null);
          }}
          onSave={handleSave}
        />
      )}
      {activeTab === "metadata" && (
        <MetadataForm
          isOpen={showForm}
          initialData={editItem as MetadataEntry | null}
          onClose={() => {
            setShowForm(false);
            setEditItem(null);
          }}
          onSave={handleSave}
        />
      )}
      {activeTab === "database-info" && (
        <DatabaseInfoForm
          isOpen={showForm}
          initialData={editItem as DatabaseInfo | null}
          onClose={() => {
            setShowForm(false);
            setEditItem(null);
          }}
          onSave={handleSave}
        />
      )}

      {/* Bulk Import */}
      <BulkImportModal
        isOpen={showImport}
        type={activeTab}
        onClose={() => setShowImport(false)}
        onImport={handleImport}
        onImportDDL={importDDL}
      />

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Delete Item"
        message="Are you sure you want to delete this item? This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={confirmDelete}
        onCancel={() => {
          setShowDeleteConfirm(false);
          setDeleteTarget(null);
        }}
        isDestructive
      />

      {/* Bulk Delete Confirmation */}
      <ConfirmDialog
        isOpen={showBulkDeleteConfirm}
        title="Delete Selected Items"
        message={`Are you sure you want to delete ${selectedIds.size} selected items? This action cannot be undone.`}
        confirmLabel="Delete All"
        onConfirm={confirmBulkDelete}
        onCancel={() => setShowBulkDeleteConfirm(false)}
        isDestructive
      />
    </div>
  );
}
