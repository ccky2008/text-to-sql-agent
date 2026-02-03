"use client";

import { useState, useEffect, useRef } from "react";
import type { EmbeddingType, DDLImportResponse } from "@/types/embeddings";

type ImportMode = "json" | "ddl";

interface BulkImportModalProps {
  isOpen: boolean;
  type: EmbeddingType;
  onClose: () => void;
  onImport: (data: unknown[]) => Promise<void>;
  onImportDDL?: (ddl: string, schemaName: string) => Promise<DDLImportResponse>;
}

const EXAMPLE_DATA: Record<EmbeddingType, string> = {
  "sql-pairs": `[
  {
    "question": "Show all users",
    "sql_query": "SELECT id, name, email FROM users"
  },
  {
    "question": "Count active orders",
    "sql_query": "SELECT COUNT(*) FROM orders WHERE status = 'active'"
  }
]`,
  metadata: `[
  {
    "title": "Active User Definition",
    "content": "A user who has logged in within the last 30 days",
    "category": "domain_term",
    "related_tables": ["users"],
    "keywords": ["active", "login", "user"]
  }
]`,
  "database-info": `[
  {
    "schema_name": "public",
    "table_name": "users",
    "description": "User accounts table",
    "columns": [
      {"name": "id", "data_type": "integer", "is_primary_key": true},
      {"name": "email", "data_type": "varchar(255)", "is_nullable": false}
    ]
  }
]`,
};

const DDL_EXAMPLE = `CREATE TABLE "users" (
  "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
  "email" character varying NOT NULL,
  "name" character varying,
  "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  CONSTRAINT "PK_users" PRIMARY KEY ("id")
);

CREATE TABLE "orders" (
  "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
  "userId" uuid NOT NULL,
  "status" character varying NOT NULL DEFAULT 'pending',
  "total" numeric(10,2) NOT NULL,
  CONSTRAINT "PK_orders" PRIMARY KEY ("id")
);`;

export function BulkImportModal({
  isOpen,
  type,
  onClose,
  onImport,
  onImportDDL,
}: BulkImportModalProps) {
  const [input, setInput] = useState("");
  const [schemaName, setSchemaName] = useState("public");
  const [mode, setMode] = useState<ImportMode>("json");
  const [error, setError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [ddlResult, setDdlResult] = useState<DDLImportResponse | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const showDDLOption = type === "database-info" && onImportDDL;

  useEffect(() => {
    if (isOpen) {
      setInput("");
      setSchemaName("public");
      setMode("json");
      setError(null);
      setDdlResult(null);
      textareaRef.current?.focus();
    }
  }, [isOpen]);

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

  const handleImport = async () => {
    setError(null);
    setDdlResult(null);

    if (!input.trim()) {
      setError(mode === "ddl" ? "Please enter DDL statements" : "Please enter JSON data");
      return;
    }

    try {
      setImporting(true);

      if (mode === "ddl" && onImportDDL) {
        const result = await onImportDDL(input, schemaName);
        setDdlResult(result);

        if (result.tables_imported > 0) {
          // Don't close immediately - show the result
          if (result.errors.length === 0) {
            setTimeout(() => onClose(), 1500);
          }
        } else if (result.errors.length > 0) {
          setError(result.errors.join("\n"));
        } else {
          setError("No tables found in DDL");
        }
      } else {
        const data = JSON.parse(input);
        if (!Array.isArray(data)) {
          setError("JSON must be an array");
          return;
        }

        if (data.length === 0) {
          setError("Array must contain at least one item");
          return;
        }

        await onImport(data);
        onClose();
      }
    } catch (e) {
      if (e instanceof SyntaxError) {
        setError(`Invalid JSON: ${e.message}`);
      } else {
        setError(e instanceof Error ? e.message : "Import failed");
      }
    } finally {
      setImporting(false);
    }
  };

  const loadExample = () => {
    if (mode === "ddl") {
      setInput(DDL_EXAMPLE);
    } else {
      setInput(EXAMPLE_DATA[type]);
    }
    setError(null);
    setDdlResult(null);
  };

  if (!isOpen) return null;

  function getTypeLabel(embeddingType: EmbeddingType): string {
    switch (embeddingType) {
      case "sql-pairs":
        return "SQL Pairs";
      case "metadata":
        return "Metadata";
      case "database-info":
        return "Database Info";
    }
  }

  const typeLabel = getTypeLabel(type);

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
        className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 p-6 max-h-[90vh] flex flex-col"
      >
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          Import {typeLabel}
        </h2>

        {/* Mode toggle for database-info */}
        {showDDLOption && (
          <div className="flex gap-2 mb-4">
            <button
              type="button"
              onClick={() => {
                setMode("json");
                setInput("");
                setError(null);
                setDdlResult(null);
              }}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                mode === "json"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              }`}
            >
              JSON
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("ddl");
                setInput("");
                setError(null);
                setDdlResult(null);
              }}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                mode === "ddl"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              }`}
            >
              DDL (CREATE TABLE)
            </button>
          </div>
        )}

        <div className="flex-1 min-h-0 flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <label
              htmlFor="import-input"
              className="text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              {mode === "ddl" ? "DDL Statements" : "JSON Data"}
            </label>
            <button
              type="button"
              onClick={loadExample}
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              Load Example
            </button>
          </div>

          {/* Schema name input for DDL mode */}
          {mode === "ddl" && (
            <div className="mb-2">
              <label
                htmlFor="schema-name"
                className="block text-xs text-gray-600 dark:text-gray-400 mb-1"
              >
                Default Schema Name
              </label>
              <input
                id="schema-name"
                type="text"
                value={schemaName}
                onChange={(e) => setSchemaName(e.target.value)}
                placeholder="public"
                className="w-48 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              />
            </div>
          )}

          <textarea
            ref={textareaRef}
            id="import-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              mode === "ddl"
                ? "Paste CREATE TABLE statements here (TypeORM DDL supported)..."
                : `Paste JSON array of ${typeLabel.toLowerCase()} here...`
            }
            className="flex-1 min-h-[200px] w-full px-3 py-2 text-sm font-mono border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />

          {/* DDL import result */}
          {ddlResult && (
            <div
              className={`mt-2 p-3 rounded-md text-sm ${
                ddlResult.errors.length > 0
                  ? "bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400"
                  : "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400"
              }`}
            >
              <p className="font-medium">
                Imported {ddlResult.tables_imported} table(s)
              </p>
              {ddlResult.tables.length > 0 && (
                <ul className="mt-1 list-disc list-inside text-xs">
                  {ddlResult.tables.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {error && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400 whitespace-pre-wrap">
              {error}
            </p>
          )}
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            type="button"
            onClick={onClose}
            disabled={importing}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors disabled:opacity-50"
          >
            {ddlResult && ddlResult.tables_imported > 0 ? "Close" : "Cancel"}
          </button>
          {!(ddlResult && ddlResult.tables_imported > 0 && ddlResult.errors.length === 0) && (
            <button
              type="button"
              onClick={handleImport}
              disabled={importing || !input.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {importing ? "Importing..." : "Import"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
