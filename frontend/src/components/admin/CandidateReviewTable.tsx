"use client";

import { useState } from "react";
import type { CandidateStatus, SQLPairCandidate } from "@/types/training-data";
import { ConfirmDialog } from "./ConfirmDialog";
import { CandidateEditForm } from "./CandidateEditForm";

const STATUS_BADGES: Record<CandidateStatus, { label: string; className: string }> = {
  pending: {
    label: "Pending",
    className: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  },
  approved: {
    label: "Approved",
    className: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  },
  rejected: {
    label: "Rejected",
    className: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  },
};

interface CandidateReviewTableProps {
  items: SQLPairCandidate[];
  selectedIds: Set<string>;
  onToggleSelection: (id: string) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
  onApprove: (id: string, question?: string, sqlQuery?: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onUpdate: (id: string, question?: string, sqlQuery?: string) => Promise<void>;
}

export function CandidateReviewTable({
  items,
  selectedIds,
  onToggleSelection,
  onSelectAll,
  onClearSelection,
  onApprove,
  onReject,
  onDelete,
  onUpdate,
}: CandidateReviewTableProps) {
  const [editingCandidate, setEditingCandidate] = useState<SQLPairCandidate | null>(null);
  const [approveEditCandidate, setApproveEditCandidate] = useState<SQLPairCandidate | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const allSelected = items.length > 0 && items.every((item) => selectedIds.has(item.id));

  const handleAction = async (id: string, action: () => Promise<void>) => {
    setActionLoading(id);
    try {
      await action();
    } finally {
      setActionLoading(null);
    }
  };

  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        No candidates found.
      </div>
    );
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-4 py-3 w-10">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={() => (allSelected ? onClearSelection() : onSelectAll())}
                  className="rounded border-gray-300 dark:border-gray-600"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Question
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                SQL Query
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Created
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
            {items.map((item) => {
              const badge = STATUS_BADGES[item.status];
              const isLoading = actionLoading === item.id;
              return (
                <tr
                  key={item.id}
                  className={
                    selectedIds.has(item.id)
                      ? "bg-blue-50 dark:bg-blue-900/20"
                      : "hover:bg-gray-50 dark:hover:bg-gray-800/50"
                  }
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(item.id)}
                      onChange={() => onToggleSelection(item.id)}
                      className="rounded border-gray-300 dark:border-gray-600"
                    />
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100 max-w-xs truncate">
                    {item.question}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 max-w-sm">
                    <code className="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded block truncate">
                      {item.sql_query}
                    </code>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.className}`}
                    >
                      {badge.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {new Date(item.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end gap-1">
                      {item.status === "pending" && (
                        <>
                          <button
                            type="button"
                            onClick={() =>
                              handleAction(item.id, () => onApprove(item.id))
                            }
                            disabled={isLoading}
                            className="px-2 py-1 text-xs font-medium text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 hover:bg-green-100 dark:hover:bg-green-900/40 rounded transition-colors disabled:opacity-50"
                          >
                            Approve
                          </button>
                          <button
                            type="button"
                            onClick={() => setApproveEditCandidate(item)}
                            disabled={isLoading}
                            className="px-2 py-1 text-xs font-medium text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/40 rounded transition-colors disabled:opacity-50"
                          >
                            Edit & Approve
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              handleAction(item.id, () => onReject(item.id))
                            }
                            disabled={isLoading}
                            className="px-2 py-1 text-xs font-medium text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 rounded transition-colors disabled:opacity-50"
                          >
                            Reject
                          </button>
                        </>
                      )}
                      <button
                        type="button"
                        onClick={() => setEditingCandidate(item)}
                        disabled={isLoading}
                        className="px-2 py-1 text-xs font-medium text-gray-700 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-50"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteConfirm(item.id)}
                        disabled={isLoading}
                        className="px-2 py-1 text-xs font-medium text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 rounded transition-colors disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Edit modal */}
      <CandidateEditForm
        isOpen={editingCandidate !== null}
        question={editingCandidate?.question ?? ""}
        sqlQuery={editingCandidate?.sql_query ?? ""}
        title="Edit Candidate"
        saveLabel="Save Changes"
        onSave={async (question, sqlQuery) => {
          if (editingCandidate) {
            await onUpdate(editingCandidate.id, question, sqlQuery);
            setEditingCandidate(null);
          }
        }}
        onCancel={() => setEditingCandidate(null)}
      />

      {/* Edit & Approve modal */}
      <CandidateEditForm
        isOpen={approveEditCandidate !== null}
        question={approveEditCandidate?.question ?? ""}
        sqlQuery={approveEditCandidate?.sql_query ?? ""}
        title="Edit & Approve"
        saveLabel="Approve"
        onSave={async (question, sqlQuery) => {
          if (approveEditCandidate) {
            await onApprove(approveEditCandidate.id, question, sqlQuery);
            setApproveEditCandidate(null);
          }
        }}
        onCancel={() => setApproveEditCandidate(null)}
      />

      {/* Delete confirmation */}
      <ConfirmDialog
        isOpen={deleteConfirm !== null}
        title="Delete Candidate"
        message="Are you sure you want to delete this candidate? This action cannot be undone."
        confirmLabel="Delete"
        isDestructive
        onConfirm={async () => {
          if (deleteConfirm) {
            await onDelete(deleteConfirm);
            setDeleteConfirm(null);
          }
        }}
        onCancel={() => setDeleteConfirm(null)}
      />
    </>
  );
}
