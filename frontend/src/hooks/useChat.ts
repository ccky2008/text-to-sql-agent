"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { queryWithStreaming } from "@/lib/api/client";
import type { SSEEventType } from "@/lib/api/types";
import type { Message, SQLResult } from "@/types/chat";

function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Load session from localStorage on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem("chat_session_id");
    if (savedSessionId) {
      setSessionId(savedSessionId);
    }
  }, []);

  // Save session to localStorage when it changes
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem("chat_session_id", sessionId);
    }
  }, [sessionId]);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || isLoading) return;

      setError(null);
      setIsLoading(true);

      // Add user message
      const userMessage: Message = {
        id: generateId(),
        role: "user",
        content: question,
        timestamp: new Date(),
      };

      // Add placeholder assistant message for streaming
      const assistantMessageId = generateId();
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);

      // Track state for building the response
      let streamedContent = "";
      let sqlResult: SQLResult | undefined;

      abortControllerRef.current = new AbortController();

      try {
        await queryWithStreaming(
          {
            question,
            session_id: sessionId,
            execute: true,
            stream: true,
          },
          (event: SSEEventType, data: Record<string, unknown>) => {
            switch (event) {
              case "sql_generated":
                sqlResult = {
                  sql: data.sql as string,
                  explanation: (data.explanation as string) || null,
                  isValid: false,
                  validationErrors: [],
                  validationWarnings: [],
                  executed: false,
                  results: null,
                  rowCount: null,
                  columns: null,
                };
                break;

              case "validation_complete":
                if (sqlResult) {
                  sqlResult.isValid = data.is_valid as boolean;
                  sqlResult.validationErrors =
                    (data.errors as string[]) || [];
                  sqlResult.validationWarnings =
                    (data.warnings as string[]) || [];
                }
                break;

              case "execution_complete":
                if (sqlResult) {
                  sqlResult.executed = data.executed as boolean;
                  sqlResult.results =
                    (data.results as Record<string, unknown>[]) || null;
                  sqlResult.rowCount = (data.row_count as number) || null;
                  sqlResult.columns = (data.columns as string[]) || null;
                }
                break;

              case "token":
                streamedContent += data.token as string;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: streamedContent, sqlResult }
                      : msg
                  )
                );
                break;

              case "response_complete":
                streamedContent = data.response as string;
                break;

              case "done":
                if (data.session_id) {
                  setSessionId(data.session_id as string);
                }
                break;

              case "error":
                setError(data.error as string);
                break;
            }
          },
          abortControllerRef.current.signal
        );

        // Finalize the assistant message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: streamedContent, sqlResult, isStreaming: false }
              : msg
          )
        );
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          // Request was cancelled, just mark as not streaming
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, isStreaming: false }
                : msg
            )
          );
        } else {
          const errorMessage =
            err instanceof Error ? err.message : "An error occurred";
          setError(errorMessage);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content: "Sorry, an error occurred while processing your request.",
                    error: errorMessage,
                    isStreaming: false,
                  }
                : msg
            )
          );
        }
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [sessionId, isLoading]
  );

  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  const clearChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setError(null);
    localStorage.removeItem("chat_session_id");
  }, []);

  return {
    messages,
    sessionId,
    isLoading,
    error,
    sendMessage,
    cancelRequest,
    clearChat,
  };
}
