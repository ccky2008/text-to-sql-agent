"use client";

import { useState, useEffect, useRef } from "react";
import type { SQLPair, SQLPairCreate, SQLPairUpdate } from "@/types/embeddings";

interface SQLPairFormProps {
  isOpen: boolean;
  initialData?: SQLPair | null;
  onClose: () => void;
  onSave: (data: SQLPairCreate | SQLPairUpdate) => Promise<void>;
}

export function SQLPairForm({
  isOpen,
  initialData,
  onClose,
  onSave,
}: SQLPairFormProps) {
  const [question, setQuestion] = useState("");
  const [sqlQuery, setSqlQuery] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const questionRef = useRef<HTMLInputElement>(null);

  const isEdit = !!initialData;

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setQuestion(initialData.question);
        setSqlQuery(initialData.sql_query);
      } else {
        setQuestion("");
        setSqlQuery("");
      }
      setError(null);
      setTimeout(() => questionRef.current?.focus(), 0);
    }
  }, [isOpen, initialData]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!question.trim()) {
      setError("Question is required");
      return;
    }

    if (!sqlQuery.trim()) {
      setError("SQL query is required");
      return;
    }

    try {
      setSaving(true);
      await onSave({
        question: question.trim(),
        sql_query: sqlQuery.trim(),
      });
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6"
      >
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {isEdit ? "Edit SQL Pair" : "Add SQL Pair"}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="question"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Question
            </label>
            <input
              ref={questionRef}
              id="question"
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Natural language question..."
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label
              htmlFor="sql-query"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              SQL Query
            </label>
            <textarea
              id="sql-query"
              value={sqlQuery}
              onChange={(e) => setSqlQuery(e.target.value)}
              placeholder="SELECT ..."
              rows={6}
              className="w-full px-3 py-2 text-sm font-mono border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? "Saving..." : isEdit ? "Update" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
