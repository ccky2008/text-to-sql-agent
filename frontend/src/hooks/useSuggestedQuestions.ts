"use client";

import { useState, useEffect, useCallback } from "react";
import { getSuggestedQuestions } from "@/lib/api/client";

interface UseSuggestedQuestionsReturn {
  questions: string[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useSuggestedQuestions(): UseSuggestedQuestionsReturn {
  const [questions, setQuestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQuestions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getSuggestedQuestions();
      setQuestions(response.questions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load suggestions");
      // Set fallback questions on error
      setQuestions([
        "How many cloud resources do I have?",
        "What are my most recently created resources?",
        "Which resources are missing tags?",
      ]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  return {
    questions,
    isLoading,
    error,
    refetch: fetchQuestions,
  };
}
