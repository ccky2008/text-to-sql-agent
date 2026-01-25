"use client";

import { useEffect, useRef } from "react";
import type { Message } from "@/types/chat";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
            <svg
              className="w-8 h-8 text-blue-600 dark:text-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
            Ask a question about your data
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            I can help you query your database using natural language. Just type
            your question below and I&apos;ll generate the SQL for you.
          </p>
          <div className="text-sm text-gray-400 dark:text-gray-500">
            <p className="mb-2">Try asking:</p>
            <ul className="space-y-1 text-left inline-block">
              <li>&quot;Show me all users created this month&quot;</li>
              <li>&quot;What are the top 10 orders by value?&quot;</li>
              <li>&quot;How many products are in each category?&quot;</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4 chat-scrollbar">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
