"use client";

import type { Message } from "@/types/chat";
import { SQLDisplay } from "./SQLDisplay";
import { ResultsTable } from "./ResultsTable";
import { StreamingIndicator } from "./StreamingIndicator";
import clsx from "clsx";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={clsx("flex w-full", isUser ? "justify-end" : "justify-start")}
    >
      <div
        className={clsx(
          "max-w-[85%] rounded-2xl px-4 py-3",
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100"
        )}
      >
        {/* Message content */}
        <div className="whitespace-pre-wrap break-words">
          {message.content}
          {message.isStreaming && !message.content && <StreamingIndicator />}
        </div>

        {/* SQL Result (for assistant messages) */}
        {!isUser && message.sqlResult && message.sqlResult.sql && (
          <SQLDisplay
            sql={message.sqlResult.sql}
            explanation={message.sqlResult.explanation}
            isValid={message.sqlResult.isValid}
            errors={message.sqlResult.validationErrors}
            warnings={message.sqlResult.validationWarnings}
          />
        )}

        {/* Query Results Table */}
        {!isUser &&
          message.sqlResult?.executed &&
          message.sqlResult.results &&
          message.sqlResult.columns && (
            <ResultsTable
              results={message.sqlResult.results}
              columns={message.sqlResult.columns}
              rowCount={message.sqlResult.rowCount || 0}
              totalCount={message.sqlResult.totalCount}
              hasMore={message.sqlResult.hasMore}
              page={message.sqlResult.page}
              pageSize={message.sqlResult.pageSize}
              queryToken={message.sqlResult.queryToken}
              csvExceedsLimit={message.sqlResult.csvExceedsLimit}
            />
          )}

        {/* Error display */}
        {message.error && (
          <div className="mt-2 p-2 rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-sm">
            {message.error}
          </div>
        )}

        {/* Timestamp */}
        <div
          className={clsx(
            "text-xs mt-2",
            isUser
              ? "text-blue-200"
              : "text-gray-400 dark:text-gray-500"
          )}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>
    </div>
  );
}
