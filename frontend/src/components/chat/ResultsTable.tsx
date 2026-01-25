"use client";

import { useState } from "react";

interface ResultsTableProps {
  results: Record<string, unknown>[];
  columns: string[];
  rowCount: number;
}

const MAX_DISPLAY_ROWS = 100;

export function ResultsTable({ results, columns, rowCount }: ResultsTableProps) {
  const [expanded, setExpanded] = useState(false);

  const displayResults = expanded ? results : results.slice(0, 10);
  const hasMore = results.length > 10;
  const isTruncated = rowCount > results.length;

  const formatValue = (value: unknown): string => {
    if (value === null || value === undefined) {
      return "NULL";
    }
    if (typeof value === "object") {
      return JSON.stringify(value);
    }
    return String(value);
  };

  return (
    <div className="my-3 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
          Results ({rowCount} row{rowCount !== 1 ? "s" : ""})
          {isTruncated && (
            <span className="ml-1 text-yellow-600 dark:text-yellow-400">
              (showing {results.length})
            </span>
          )}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              {columns.map((column) => (
                <th
                  key={column}
                  className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
            {displayResults.map((row, i) => (
              <tr
                key={i}
                className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                {columns.map((column) => (
                  <td
                    key={column}
                    className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100 whitespace-nowrap"
                  >
                    <span
                      className={
                        row[column] === null
                          ? "text-gray-400 dark:text-gray-500 italic"
                          : ""
                      }
                    >
                      {formatValue(row[column])}
                    </span>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {hasMore && (
        <div className="px-4 py-2 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
          >
            {expanded
              ? "Show less"
              : `Show more (${Math.min(results.length, MAX_DISPLAY_ROWS) - 10} more rows)`}
          </button>
        </div>
      )}
    </div>
  );
}
