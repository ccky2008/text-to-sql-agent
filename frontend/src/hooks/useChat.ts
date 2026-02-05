"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { queryWithStreaming } from "@/lib/api/client";
import type { SSEEventType } from "@/lib/api/types";
import type { AgentStep, Message, SQLResult } from "@/types/chat";

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
      let suggestedQuestions: string[] = [];
      let steps: AgentStep[] = [];

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
              case "step_started":
                // Mark any currently active step as completed
                steps = steps.map((s) =>
                  s.status === "active"
                    ? { ...s, status: "completed" as const }
                    : s
                );
                // Add the new active step
                steps = [
                  ...steps,
                  {
                    name: data.step as string,
                    label: data.label as string,
                    status: "active" as const,
                  },
                ];
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, steps }
                      : msg
                  )
                );
                break;

              case "step_completed":
                steps = steps.map((s) =>
                  s.name === (data.step as string)
                    ? { ...s, status: "completed" as const }
                    : s
                );
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, steps }
                      : msg
                  )
                );
                break;

              case "sql_generated":
                sqlResult = {
                  sql: data.sql as string,
                  explanation: (data.explanation as string) ?? null,
                  isValid: false,
                  validationErrors: [],
                  validationWarnings: [],
                  executed: false,
                  results: null,
                  rowCount: null,
                  columns: null,
                  // Pagination defaults
                  totalCount: null,
                  hasMore: false,
                  page: 1,
                  pageSize: 100,
                  // CSV defaults
                  csvAvailable: false,
                  csvExceedsLimit: false,
                  queryToken: null,
                };
                break;

              case "validation_complete":
                if (sqlResult) {
                  sqlResult.isValid = data.is_valid as boolean;
                  sqlResult.validationErrors =
                    (data.errors as string[]) ?? [];
                  sqlResult.validationWarnings =
                    (data.warnings as string[]) ?? [];
                }
                break;

              case "execution_complete":
                if (sqlResult) {
                  sqlResult.executed = true;
                  sqlResult.results =
                    (data.results as Record<string, unknown>[]) ?? null;
                  sqlResult.rowCount = (data.row_count as number) ?? null;
                  sqlResult.columns = (data.columns as string[]) ?? null;
                  sqlResult.totalCount = (data.total_count as number) ?? null;
                  sqlResult.hasMore = (data.has_more as boolean) ?? false;
                  sqlResult.page = (data.page as number) ?? 1;
                  sqlResult.pageSize = (data.page_size as number) ?? 100;
                  sqlResult.csvAvailable = (data.csv_available as boolean) ?? false;
                  sqlResult.csvExceedsLimit = (data.csv_exceeds_limit as boolean) ?? false;
                  sqlResult.queryToken = (data.query_token as string) ?? null;
                }
                break;

              case "tool_execution_complete":
                // Handle LLM-driven tool execution results
                if (data.success) {
                  const totalCount = (data.total_count as number) ?? null;
                  const CSV_MAX_ROWS = 2500;

                  // Initialize sqlResult if not already set
                  sqlResult = sqlResult ?? {
                    sql: "",
                    explanation: null,
                    isValid: true,
                    validationErrors: [],
                    validationWarnings: [],
                    executed: false,
                    results: null,
                    rowCount: null,
                    columns: null,
                    totalCount: null,
                    hasMore: false,
                    page: 1,
                    pageSize: 100,
                    csvAvailable: false,
                    csvExceedsLimit: false,
                    queryToken: null,
                  };

                  // Update with tool execution results
                  sqlResult = {
                    ...sqlResult,
                    executed: true,
                    executedViaTool: true,
                    results: (data.rows as Record<string, unknown>[]) ?? null,
                    rowCount: (data.row_count as number) ?? 0,
                    columns: (data.columns as string[]) ?? null,
                    totalCount,
                    hasMore: (data.has_more as boolean) ?? false,
                    page: (data.page as number) ?? 1,
                    pageSize: (data.page_size as number) ?? 100,
                    queryToken: (data.query_token as string) ?? null,
                    csvAvailable: !!data.query_token,
                    csvExceedsLimit: totalCount !== null && totalCount > CSV_MAX_ROWS,
                  };

                  // Update the message immediately to show results
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessageId
                        ? { ...msg, sqlResult }
                        : msg
                    )
                  );
                } else if (data.error) {
                  setError(data.error as string);
                }
                break;

              case "token":
                streamedContent += data.content as string;
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

              case "suggested_questions":
                suggestedQuestions = (data.questions as string[]) ?? [];
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, suggestedQuestions }
                      : msg
                  )
                );
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
              ? {
                  ...msg,
                  content: streamedContent,
                  sqlResult,
                  suggestedQuestions,
                  isStreaming: false,
                }
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
