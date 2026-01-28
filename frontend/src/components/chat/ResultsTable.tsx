"use client";

import { useState } from "react";
import { Pagination } from "./Pagination";
import { CSVDownloadButton } from "./CSVDownloadButton";

interface ResultsTableProps {
  results: Record<string, unknown>[];
  columns: string[];
  rowCount: number;
  // Pagination props
  totalCount?: number | null;
  hasMore?: boolean;
  page?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  isLoadingPage?: boolean;
  // CSV props
  queryToken?: string | null;
  csvExceedsLimit?: boolean;
}

const MAX_DISPLAY_ROWS = 100;

export function ResultsTable({
  results,
  columns,
  rowCount,
  totalCount,
  hasMore,
  page = 1,
  pageSize = 100,
  onPageChange,
  isLoadingPage,
  queryToken,
  csvExceedsLimit,
}: ResultsTableProps) {
  const [expanded, setExpanded] = useState(false);

  // Cap to MAX_DISPLAY_ROWS to prevent DOM performance issues
  const displayResults = expanded
    ? results.slice(0, MAX_DISPLAY_ROWS)
    : results.slice(0, 10);
  const hasMoreLocal = results.length > 10;
  const totalPages =
    totalCount && pageSize ? Math.ceil(totalCount / pageSize) : null;

  const displayTotal = totalCount ?? rowCount;
  const showPaginationInfo = totalCount != null;

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
    <div className="relative my-3 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
          Results ({(displayTotal ?? 0).toLocaleString()} total
          {showPaginationInfo && ` | showing ${results.length} on page ${page}`}
          )
        </span>

        {/* CSV Download Button - show whenever we have a valid query token */}
        {queryToken && (
          <CSVDownloadButton
            queryToken={queryToken}
            totalCount={totalCount ?? null}
            csvExceedsLimit={csvExceedsLimit ?? false}
          />
        )}
      </div>

      {/* Loading overlay */}
      {isLoadingPage && (
        <div className="absolute inset-0 bg-white/50 dark:bg-gray-900/50 flex items-center justify-center" role="status">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" />
          <span className="sr-only">Loading page results</span>
        </div>
      )}

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

      {/* Local expand/collapse for rows on current page */}
      {hasMoreLocal && (
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

      {/* Pagination controls */}
      {onPageChange && totalPages && totalPages > 1 && (
        <div className="border-t border-gray-200 dark:border-gray-700">
          <Pagination
            page={page}
            totalPages={totalPages}
            hasNext={hasMore ?? false}
            hasPrev={page > 1}
            onPageChange={onPageChange}
            disabled={isLoadingPage}
          />
        </div>
      )}
    </div>
  );
}
