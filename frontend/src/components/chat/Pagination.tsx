"use client";

interface PaginationProps {
  page: number;
  totalPages: number | null;
  hasNext: boolean;
  hasPrev: boolean;
  onPageChange: (page: number) => void;
  disabled?: boolean;
}

export function Pagination({
  page,
  totalPages,
  hasNext,
  hasPrev,
  onPageChange,
  disabled,
}: PaginationProps) {
  return (
    <nav className="flex items-center justify-center gap-2 py-2" aria-label="Pagination">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={!hasPrev || disabled}
        aria-label="Go to previous page"
        className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600
                   disabled:opacity-50 disabled:cursor-not-allowed
                   hover:bg-gray-100 dark:hover:bg-gray-700"
      >
        Previous
      </button>

      <span className="text-sm text-gray-600 dark:text-gray-400" aria-current="page">
        Page {page}
        {totalPages && ` of ${totalPages}`}
      </span>

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={!hasNext || disabled}
        aria-label="Go to next page"
        className="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600
                   disabled:opacity-50 disabled:cursor-not-allowed
                   hover:bg-gray-100 dark:hover:bg-gray-700"
      >
        Next
      </button>
    </nav>
  );
}
