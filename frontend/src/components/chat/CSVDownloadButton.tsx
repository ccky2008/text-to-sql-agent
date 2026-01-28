"use client";

import { useState } from "react";
import { downloadCSV } from "@/lib/api/client";

interface CSVDownloadButtonProps {
  queryToken: string;
  totalCount: number | null;
  csvExceedsLimit: boolean;
  maxRows?: number;
}

export function CSVDownloadButton({
  queryToken,
  totalCount,
  csvExceedsLimit,
  maxRows = 2500,
}: CSVDownloadButtonProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [showWarning, setShowWarning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    if (csvExceedsLimit && !showWarning) {
      setShowWarning(true);
      return;
    }

    setIsDownloading(true);
    setError(null);
    try {
      await downloadCSV({
        query_token: queryToken,
        limit: maxRows,
        filename: `query_results_${Date.now()}.csv`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Download failed";
      setError(message);
    } finally {
      setIsDownloading(false);
      setShowWarning(false);
    }
  };

  return (
    <div className="relative inline-block">
      <button
        onClick={handleDownload}
        disabled={isDownloading}
        className="flex items-center gap-1 px-3 py-1 text-xs font-medium
                   text-blue-600 hover:text-blue-800 dark:text-blue-400
                   dark:hover:text-blue-300 disabled:opacity-50"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        {isDownloading ? "Downloading..." : "Download CSV"}
      </button>

      {error && (
        <p className="absolute right-0 top-full mt-1 text-xs text-red-600 dark:text-red-400 whitespace-nowrap">
          {error}
        </p>
      )}

      {showWarning && (
        <div
          className="absolute right-0 top-full mt-1 w-64 p-3 bg-yellow-50
                        dark:bg-yellow-900/30 border border-yellow-200
                        dark:border-yellow-700 rounded-lg shadow-lg z-10"
        >
          <p className="text-xs text-yellow-800 dark:text-yellow-200 mb-2">
            This dataset has {totalCount?.toLocaleString()} rows. Only the first{" "}
            {maxRows.toLocaleString()} will be downloaded.
          </p>
          <p className="text-xs text-yellow-700 dark:text-yellow-300 mb-2">
            For more data, ask the assistant to fetch in batches (e.g., &quot;Get
            me records 2501 to 5000&quot;).
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleDownload}
              className="text-xs px-2 py-1 bg-yellow-600 text-white rounded hover:bg-yellow-700"
            >
              Download First {maxRows.toLocaleString()}
            </button>
            <button
              onClick={() => setShowWarning(false)}
              className="text-xs px-2 py-1 border border-yellow-600 text-yellow-700
                         dark:text-yellow-300 rounded hover:bg-yellow-100 dark:hover:bg-yellow-800"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
