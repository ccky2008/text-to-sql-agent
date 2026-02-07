"use client";

import type { Message } from "@/types/chat";
import { SQLDisplay } from "./SQLDisplay";
import { ResultsTable } from "./ResultsTable";
import { StepProgress } from "./StepProgress";
import { StreamingIndicator } from "./StreamingIndicator";
import { SuggestedQuestions } from "./SuggestedQuestions";
import clsx from "clsx";

interface MessageBubbleProps {
  message: Message;
  onSelectQuestion?: (question: string) => void;
}

export function MessageBubble({ message, onSelectQuestion }: MessageBubbleProps) {
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
        {/* Step progress (replaces generic streaming indicator when steps available) */}
        {message.isStreaming && message.steps && message.steps.length > 0 && (
          <StepProgress steps={message.steps} />
        )}

        {/* Clarification indicator */}
        {!isUser && message.isClarification && (
          <div className="flex items-center gap-1.5 mb-2 text-amber-600 dark:text-amber-400 text-xs font-medium">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
              className="w-3.5 h-3.5"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM8.94 6.94a.75.75 0 11-1.061-1.061 3 3 0 112.871 5.026v.345a.75.75 0 01-1.5 0v-.5c0-.72.57-1.172 1.081-1.287A1.5 1.5 0 108.94 6.94zM10 15a1 1 0 100-2 1 1 0 000 2z"
                clipRule="evenodd"
              />
            </svg>
            Clarifying question
          </div>
        )}

        {/* Message content */}
        <div className="whitespace-pre-wrap break-words">
          {message.content}
          {message.isStreaming &&
            !message.content &&
            (!message.steps || message.steps.length === 0) && (
              <StreamingIndicator />
            )}
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

        {/* Follow-up questions (for completed assistant messages) */}
        {!isUser &&
          !message.isStreaming &&
          message.suggestedQuestions &&
          message.suggestedQuestions.length > 0 &&
          onSelectQuestion && (
            <SuggestedQuestions
              questions={message.suggestedQuestions}
              onSelect={onSelectQuestion}
              variant="follow_up"
            />
          )}
      </div>
    </div>
  );
}
