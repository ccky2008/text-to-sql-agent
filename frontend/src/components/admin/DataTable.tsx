"use client";

import type { SQLPair, MetadataEntry, DatabaseInfo } from "@/types/embeddings";

interface DataTableProps<T> {
  items: T[];
  selectedIds: Set<string>;
  onToggleSelection: (id: string) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
  onEdit: (item: T) => void;
  onDelete: (item: T) => void;
  type: "sql-pairs" | "metadata" | "database-info";
}

export function DataTable<T extends SQLPair | MetadataEntry | DatabaseInfo>({
  items,
  selectedIds,
  onToggleSelection,
  onSelectAll,
  onClearSelection,
  onEdit,
  onDelete,
  type,
}: DataTableProps<T>) {
  const allSelected = items.length > 0 && items.every((item) => selectedIds.has(item.id));
  const someSelected = items.some((item) => selectedIds.has(item.id)) && !allSelected;

  const handleSelectAllChange = () => {
    if (allSelected) {
      onClearSelection();
    } else {
      onSelectAll();
    }
  };

  if (items.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        No items found. Click &quot;Add New&quot; to create one.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-gray-700">
            <th className="w-10 px-4 py-3 text-left">
              <input
                type="checkbox"
                checked={allSelected}
                ref={(el) => {
                  if (el) el.indeterminate = someSelected;
                }}
                onChange={handleSelectAllChange}
                className="rounded border-gray-300 dark:border-gray-600"
              />
            </th>
            <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">
              ID
            </th>
            {type === "sql-pairs" && (
              <>
                <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">
                  Question
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">
                  SQL Query
                </th>
              </>
            )}
            {type === "metadata" && (
              <>
                <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">
                  Title
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">
                  Category
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">
                  Content
                </th>
              </>
            )}
            {type === "database-info" && (
              <>
                <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">
                  Table
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">
                  Columns
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">
                  Description
                </th>
              </>
            )}
            <th className="w-32 px-4 py-3 text-right font-medium text-gray-700 dark:text-gray-300">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
            >
              <td className="px-4 py-3">
                <input
                  type="checkbox"
                  checked={selectedIds.has(item.id)}
                  onChange={() => onToggleSelection(item.id)}
                  className="rounded border-gray-300 dark:border-gray-600"
                />
              </td>
              <td className="px-4 py-3 font-mono text-xs text-gray-500 dark:text-gray-400">
                {item.id.slice(0, 8)}...
              </td>

              {type === "sql-pairs" && (
                <>
                  <td className="px-4 py-3 max-w-xs truncate text-gray-900 dark:text-gray-100">
                    {(item as SQLPair).question}
                  </td>
                  <td className="px-4 py-3 max-w-sm truncate font-mono text-xs text-gray-600 dark:text-gray-400">
                    {(item as SQLPair).sql_query}
                  </td>
                </>
              )}

              {type === "metadata" && (
                <>
                  <td className="px-4 py-3 max-w-xs truncate text-gray-900 dark:text-gray-100">
                    {(item as MetadataEntry).title}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                      {(item as MetadataEntry).category.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3 max-w-sm truncate text-gray-600 dark:text-gray-400">
                    {(item as MetadataEntry).content}
                  </td>
                </>
              )}

              {type === "database-info" && (
                <>
                  <td className="px-4 py-3 font-mono text-sm text-gray-900 dark:text-gray-100">
                    {(item as DatabaseInfo).full_name}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {(item as DatabaseInfo).columns.length} columns
                  </td>
                  <td className="px-4 py-3 max-w-sm truncate text-gray-600 dark:text-gray-400">
                    {(item as DatabaseInfo).description || "-"}
                  </td>
                </>
              )}

              <td className="px-4 py-3 text-right">
                <button
                  type="button"
                  onClick={() => onEdit(item)}
                  className="text-blue-600 dark:text-blue-400 hover:underline text-sm mr-3"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(item)}
                  className="text-red-600 dark:text-red-400 hover:underline text-sm"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
