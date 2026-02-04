"use client";

import { useState, useEffect, useRef } from "react";
import type {
  DatabaseInfo,
  DatabaseInfoCreate,
  DatabaseInfoUpdate,
  ColumnInfo,
} from "@/types/embeddings";

interface DatabaseInfoFormProps {
  isOpen: boolean;
  initialData?: DatabaseInfo | null;
  onClose: () => void;
  onSave: (data: DatabaseInfoCreate | DatabaseInfoUpdate) => Promise<void>;
}

const DEFAULT_COLUMN: ColumnInfo = {
  name: "",
  data_type: "varchar",
  is_nullable: true,
  is_primary_key: false,
  is_foreign_key: false,
  foreign_key_table: null,
  foreign_key_column: null,
  default_value: null,
  description: null,
};

export function DatabaseInfoForm({
  isOpen,
  initialData,
  onClose,
  onSave,
}: DatabaseInfoFormProps) {
  const [schemaName, setSchemaName] = useState("public");
  const [tableName, setTableName] = useState("");
  const [description, setDescription] = useState("");
  const [columns, setColumns] = useState<ColumnInfo[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tableNameRef = useRef<HTMLInputElement>(null);

  const isEdit = !!initialData;

  useEffect(() => {
    if (isOpen) {
      if (initialData) {
        setSchemaName(initialData.schema_name);
        setTableName(initialData.table_name);
        setDescription(initialData.description || "");
        setColumns(
          initialData.columns.length > 0
            ? initialData.columns
            : [{ ...DEFAULT_COLUMN }]
        );
      } else {
        setSchemaName("public");
        setTableName("");
        setDescription("");
        setColumns([{ ...DEFAULT_COLUMN }]);
      }
      setError(null);
      setTimeout(() => tableNameRef.current?.focus(), 0);
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

  const addColumn = () => {
    setColumns([...columns, { ...DEFAULT_COLUMN }]);
  };

  const removeColumn = (index: number) => {
    setColumns(columns.filter((_, i) => i !== index));
  };

  const updateColumn = (
    index: number,
    field: keyof ColumnInfo,
    value: string | boolean | null
  ) => {
    const newColumns = [...columns];
    newColumns[index] = { ...newColumns[index], [field]: value };
    setColumns(newColumns);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!tableName.trim()) {
      setError("Table name is required");
      return;
    }

    const validColumns = columns.filter((col) => col.name.trim());

    try {
      setSaving(true);
      await onSave({
        schema_name: schemaName.trim() || "public",
        table_name: tableName.trim(),
        description: description.trim() || undefined,
        columns: validColumns,
        relationships: [],
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
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full mx-4 p-6 max-h-[90vh] overflow-y-auto"
      >
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {isEdit ? "Edit Database Info" : "Add Database Info"}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="schema-name"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Schema Name
              </label>
              <input
                id="schema-name"
                type="text"
                value={schemaName}
                onChange={(e) => setSchemaName(e.target.value)}
                placeholder="public"
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label
                htmlFor="table-name"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Table Name
              </label>
              <input
                ref={tableNameRef}
                id="table-name"
                type="text"
                value={tableName}
                onChange={(e) => setTableName(e.target.value)}
                placeholder="users"
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label
              htmlFor="description"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Table description..."
              rows={2}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Columns
              </label>
              <button
                type="button"
                onClick={addColumn}
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                + Add Column
              </button>
            </div>

            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {columns.map((column, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-900 rounded-md"
                >
                  <input
                    type="text"
                    value={column.name}
                    onChange={(e) => updateColumn(index, "name", e.target.value)}
                    placeholder="Column name"
                    className="flex-1 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  />
                  <input
                    type="text"
                    value={column.data_type}
                    onChange={(e) =>
                      updateColumn(index, "data_type", e.target.value)
                    }
                    placeholder="Data type"
                    className="w-32 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                  />
                  <label className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                    <input
                      type="checkbox"
                      checked={column.is_primary_key}
                      onChange={(e) =>
                        updateColumn(index, "is_primary_key", e.target.checked)
                      }
                      className="rounded border-gray-300"
                    />
                    PK
                  </label>
                  <label className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400">
                    <input
                      type="checkbox"
                      checked={column.is_nullable}
                      onChange={(e) =>
                        updateColumn(index, "is_nullable", e.target.checked)
                      }
                      className="rounded border-gray-300"
                    />
                    Null
                  </label>
                  <button
                    type="button"
                    onClick={() => removeColumn(index)}
                    className="text-red-500 hover:text-red-700 text-sm px-2"
                    disabled={columns.length === 1}
                  >
                    X
                  </button>
                </div>
              ))}
            </div>
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
