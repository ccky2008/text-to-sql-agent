"use client";

import clsx from "clsx";

interface SuggestedQuestionsProps {
  questions: string[];
  onSelect: (question: string) => void;
  variant?: "initial" | "follow_up";
  isLoading?: boolean;
}

export function SuggestedQuestions({
  questions,
  onSelect,
  variant = "initial",
  isLoading = false,
}: SuggestedQuestionsProps) {
  if (isLoading) {
    return (
      <div className="flex flex-wrap gap-2">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-8 w-48 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (questions.length === 0) {
    return null;
  }

  const isInitial = variant === "initial";

  return (
    <div
      className={clsx(
        "flex flex-wrap gap-2",
        isInitial ? "justify-center" : "justify-start mt-3"
      )}
    >
      {questions.map((question, index) => (
        <button
          key={index}
          onClick={() => onSelect(question)}
          className={clsx(
            "px-3 py-1.5 rounded-full text-sm font-medium transition-all",
            "border hover:shadow-sm",
            "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1",
            isInitial
              ? "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-blue-400 dark:hover:border-blue-500"
              : "bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50"
          )}
        >
          {question}
        </button>
      ))}
    </div>
  );
}
