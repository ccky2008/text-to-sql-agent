"use client";

import { useChat } from "@/hooks/useChat";
import { useSuggestedQuestions } from "@/hooks/useSuggestedQuestions";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";

export function ChatContainer() {
  const {
    messages,
    sessionId,
    isLoading,
    error,
    sendMessage,
    cancelRequest,
    clearChat,
  } = useChat();

  const {
    questions: initialQuestions,
    isLoading: initialQuestionsLoading,
  } = useSuggestedQuestions();

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
            <svg
              className="w-5 h-5 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
              />
            </svg>
          </div>
          <div>
            <h1 className="font-semibold text-gray-900 dark:text-gray-100">
              Text to SQL
            </h1>
            {sessionId && (
              <p className="text-xs text-gray-400 dark:text-gray-500">
                Session: {sessionId.slice(0, 8)}...
              </p>
            )}
          </div>
        </div>

        <button
          onClick={clearChat}
          className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          New Chat
        </button>
      </header>

      {/* Error banner */}
      {error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Messages */}
      <MessageList
        messages={messages}
        initialQuestions={initialQuestions}
        initialQuestionsLoading={initialQuestionsLoading}
        onSelectQuestion={sendMessage}
      />

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        onCancel={cancelRequest}
        disabled={isLoading}
        isLoading={isLoading}
      />
    </div>
  );
}
