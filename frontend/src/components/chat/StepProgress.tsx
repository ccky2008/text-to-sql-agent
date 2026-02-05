"use client";

import type { AgentStep } from "@/types/chat";

interface StepProgressProps {
  steps: AgentStep[];
}

export function StepProgress({ steps }: StepProgressProps) {
  if (steps.length === 0) return null;

  return (
    <div className="flex flex-col gap-1 py-1">
      {steps.map((step) => (
        <div key={step.name} className="flex items-center gap-2 text-sm">
          {step.status === "active" ? (
            <span className="w-4 h-4 flex items-center justify-center">
              <span className="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </span>
          ) : (
            <span className="w-4 h-4 flex items-center justify-center text-green-500">
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </span>
          )}
          <span
            className={
              step.status === "active"
                ? "text-gray-900 dark:text-gray-100 font-medium"
                : "text-gray-400 dark:text-gray-500"
            }
          >
            {step.label}
            {step.status === "active" && "..."}
          </span>
        </div>
      ))}
    </div>
  );
}
