"use client";

import { useState, useEffect, useRef } from "react";
import type {
  MetadataEntry,
  MetadataCreate,
  MetadataUpdate,
  MetadataCategory,
} from "@/types/embeddings";

interface MetadataFormProps {
  isOpen: boolean;
  initialData?: MetadataEntry | null;
  onClose: () => void;
  onSave: (data: MetadataCreate | MetadataUpdate) => Promise<void>;
}

const CATEGORIES: { value: MetadataCategory; label: string }[] = [
  { value: "business_rule", label: "Business Rule" },
  { value: "domain_term", label: "Domain Term" },
  { value: "context", label: "Context" },
];

export function MetadataForm({
  isOpen,
  initialData,
  onClose,
  onSave,
}: MetadataFormProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState<MetadataCategory>("context");
  const [relatedTables, setRelatedTables] = useState("");
  const [keywords, setKeywords] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const titleRef = useRef<HTMLInputElement>(null);

  const isEdit = !!initialData;

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setTitle(initialData.title);
        setContent(initialData.content);
        setCategory(initialData.category);
        setRelatedTables(initialData.related_tables.join(", "));
        setKeywords(initialData.keywords.join(", "));
      } else {
        setTitle("");
        setContent("");
        setCategory("context");
        setRelatedTables("");
        setKeywords("");
      }
      setError(null);
      setTimeout(() => titleRef.current?.focus(), 0);
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

    if (!title.trim()) {
      setError("Title is required");
      return;
    }

    if (!content.trim()) {
      setError("Content is required");
      return;
    }

    const parsedTables = relatedTables
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    const parsedKeywords = keywords
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);

    try {
      setSaving(true);
      await onSave({
        title: title.trim(),
        content: content.trim(),
        category,
        related_tables: parsedTables,
        keywords: parsedKeywords,
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
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6 max-h-[90vh] overflow-y-auto"
      >
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {isEdit ? "Edit Metadata" : "Add Metadata"}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="title"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Title
            </label>
            <input
              ref={titleRef}
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Metadata title..."
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label
              htmlFor="content"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Content
            </label>
            <textarea
              id="content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Description or content..."
              rows={4}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          <div>
            <label
              htmlFor="category"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Category
            </label>
            <select
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value as MetadataCategory)}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="related-tables"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Related Tables (comma-separated)
            </label>
            <input
              id="related-tables"
              type="text"
              value={relatedTables}
              onChange={(e) => setRelatedTables(e.target.value)}
              placeholder="users, orders, products"
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label
              htmlFor="keywords"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Keywords (comma-separated)
            </label>
            <input
              id="keywords"
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="keyword1, keyword2, keyword3"
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
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
