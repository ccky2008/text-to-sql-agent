"use client";

import { useEffect, useRef, useState } from "react";

interface CandidateEditFormProps {
  isOpen: boolean;
  question: string;
  sqlQuery: string;
  onSave: (question: string, sqlQuery: string) => void;
  onCancel: () => void;
  title?: string;
  saveLabel?: string;
}

export function CandidateEditForm({
  isOpen,
  question,
  sqlQuery,
  onSave,
  onCancel,
  title = "Edit Candidate",
  saveLabel = "Save",
}: CandidateEditFormProps) {
  const [editQuestion, setEditQuestion] = useState(question);
  const [editSql, setEditSql] = useState(sqlQuery);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      setEditQuestion(question);
      setEditSql(sqlQuery);
      dialogRef.current?.focus();
    }
  }, [isOpen, question, sqlQuery]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") {
        onCancel();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0 bg-black/50"
        onClick={onCancel}
        aria-hidden="true"
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-dialog-title"
        tabIndex={-1}
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6"
      >
        <h2
          id="edit-dialog-title"
          className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4"
        >
          {title}
        </h2>
        <div className="space-y-4">
          <div>
            <label
              htmlFor="edit-question"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Question
            </label>
            <input
              id="edit-question"
              type="text"
              value={editQuestion}
              onChange={(e) => setEditQuestion(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <div>
            <label
              htmlFor="edit-sql"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              SQL Query
            </label>
            <textarea
              id="edit-sql"
              value={editSql}
              onChange={(e) => setEditSql(e.target.value)}
              rows={6}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onSave(editQuestion, editSql)}
            disabled={!editQuestion.trim() || !editSql.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saveLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
