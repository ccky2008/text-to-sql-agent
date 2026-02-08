"use client";

import { useState } from "react";
import { useTrainingData } from "@/hooks/useTrainingData";
import { Pagination, ConfirmDialog } from "@/components/admin";
import { CandidateReviewTable } from "@/components/admin/CandidateReviewTable";
import type { CandidateStatus } from "@/types/training-data";

const STATUS_TABS: { id: CandidateStatus | undefined; label: string }[] = [
  { id: "pending", label: "Pending" },
  { id: "approved", label: "Approved" },
  { id: "rejected", label: "Rejected" },
  { id: undefined, label: "All" },
];

export default function TrainingDataPage() {
  const {
    items,
    total,
    page,
    pageSize,
    hasNext,
    hasPrev,
    statusFilter,
    counts,
    selectedIds,
    loading,
    error,
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
  } = useTrainingData();

  const [bulkApproveConfirm, setBulkApproveConfirm] = useState(false);
  const [bulkRejectConfirm, setBulkRejectConfirm] = useState(false);

  const getTabCount = (status: CandidateStatus | undefined): number =>
    status ? counts[status] : counts.total;

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Training Data Review
        </h2>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Review auto-generated SQL pair candidates and approve them as training data.
        </p>
      </div>

      {/* Status tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 mb-4">
        <nav className="-mb-px flex space-x-6">
          {STATUS_TABS.map((tab) => {
            const isActive = statusFilter === tab.id;
            const count = getTabCount(tab.id);
            return (
              <button
                key={tab.label}
                type="button"
                onClick={() => setStatusFilter(tab.id)}
                className={`whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                  isActive
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300"
                }`}
              >
                {tab.label}
                <span
                  className={`ml-2 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    isActive
                      ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
                      : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bulk actions bar */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <span className="text-sm font-medium text-blue-800 dark:text-blue-300">
            {selectedIds.size} selected
          </span>
          <button
            type="button"
            onClick={() => setBulkApproveConfirm(true)}
            className="px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors"
          >
            Approve Selected
          </button>
          <button
            type="button"
            onClick={() => setBulkRejectConfirm(true)}
            className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors"
          >
            Reject Selected
          </button>
          <button
            type="button"
            onClick={clearSelection}
            className="px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-md transition-colors"
          >
            Clear
          </button>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          Loading...
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          <CandidateReviewTable
            items={items}
            selectedIds={selectedIds}
            onToggleSelection={toggleSelection}
            onSelectAll={selectAll}
            onClearSelection={clearSelection}
            onApprove={handleApprove}
            onReject={handleReject}
            onDelete={handleDelete}
            onUpdate={handleUpdate}
          />
          <Pagination
            page={page}
            total={total}
            pageSize={pageSize}
            hasNext={hasNext}
            hasPrev={hasPrev}
            onPageChange={setPage}
          />
        </div>
      )}

      {/* Bulk approve confirmation */}
      <ConfirmDialog
        isOpen={bulkApproveConfirm}
        title="Bulk Approve"
        message={`Approve ${selectedIds.size} candidate(s) and add them to ChromaDB as training data?`}
        confirmLabel="Approve All"
        onConfirm={async () => {
          await handleBulkApprove();
          setBulkApproveConfirm(false);
        }}
        onCancel={() => setBulkApproveConfirm(false)}
      />

      {/* Bulk reject confirmation */}
      <ConfirmDialog
        isOpen={bulkRejectConfirm}
        title="Bulk Reject"
        message={`Reject ${selectedIds.size} candidate(s)?`}
        confirmLabel="Reject All"
        isDestructive
        onConfirm={async () => {
          await handleBulkReject();
          setBulkRejectConfirm(false);
        }}
        onCancel={() => setBulkRejectConfirm(false)}
      />
    </div>
  );
}
