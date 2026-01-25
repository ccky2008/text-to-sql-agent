"use client";

export function StreamingIndicator() {
  return (
    <div className="flex items-center gap-1.5 text-gray-400">
      <span
        className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"
        style={{ animationDelay: "0ms" }}
      />
      <span
        className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"
        style={{ animationDelay: "150ms" }}
      />
      <span
        className="w-1.5 h-1.5 bg-current rounded-full animate-bounce"
        style={{ animationDelay: "300ms" }}
      />
    </div>
  );
}
