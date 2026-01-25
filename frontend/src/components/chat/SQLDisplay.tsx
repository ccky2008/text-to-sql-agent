"use client";

import { useState } from "react";
import { Highlight, themes } from "prism-react-renderer";

interface SQLDisplayProps {
  sql: string;
  explanation?: string | null;
  isValid?: boolean;
  errors?: string[];
  warnings?: string[];
}

export function SQLDisplay({
  sql,
  explanation,
  isValid = true,
  errors = [],
  warnings = [],
}: SQLDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            SQL
          </span>
          {isValid ? (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
              Valid
            </span>
          ) : (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
              Invalid
            </span>
          )}
        </div>
        <button
          onClick={handleCopy}
          className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      <Highlight theme={themes.nightOwl} code={sql.trim()} language="sql">
        {({ style, tokens, getLineProps, getTokenProps }) => (
          <pre
            style={style}
            className="p-4 overflow-x-auto text-sm leading-relaxed"
          >
            {tokens.map((line, i) => (
              <div key={i} {...getLineProps({ line })}>
                {line.map((token, key) => (
                  <span key={key} {...getTokenProps({ token })} />
                ))}
              </div>
            ))}
          </pre>
        )}
      </Highlight>

      {errors.length > 0 && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800">
          <p className="text-xs font-medium text-red-800 dark:text-red-200 mb-1">
            Errors:
          </p>
          <ul className="text-xs text-red-700 dark:text-red-300 list-disc list-inside">
            {errors.map((error, i) => (
              <li key={i}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="px-4 py-2 bg-yellow-50 dark:bg-yellow-900/20 border-t border-yellow-200 dark:border-yellow-800">
          <p className="text-xs font-medium text-yellow-800 dark:text-yellow-200 mb-1">
            Warnings:
          </p>
          <ul className="text-xs text-yellow-700 dark:text-yellow-300 list-disc list-inside">
            {warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {explanation && (
        <div className="px-4 py-2 bg-blue-50 dark:bg-blue-900/20 border-t border-blue-200 dark:border-blue-800">
          <p className="text-xs font-medium text-blue-800 dark:text-blue-200 mb-1">
            Explanation:
          </p>
          <p className="text-xs text-blue-700 dark:text-blue-300">
            {explanation}
          </p>
        </div>
      )}
    </div>
  );
}
