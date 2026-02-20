/**
 * Error display component with actionable suggestions
 */

"use client";

import React from "react";
import { AlertCircle, X, RefreshCw, ChevronDown } from "lucide-react";
import { ApiError, getErrorSeverity } from "@/lib/errorHandling";

interface ErrorDisplayProps {
  error: ApiError | null;
  onDismiss?: () => void;
  onRetry?: () => void;
  showDetails?: boolean;
}

export function ErrorDisplay({
  error,
  onDismiss,
  onRetry,
  showDetails = true,
}: ErrorDisplayProps) {
  const [showMore, setShowMore] = React.useState(false);

  if (!error) return null;

  const severity = getErrorSeverity(error.error_code);
  const bgColor =
    severity === "error"
      ? "bg-red-50 border-red-200"
      : severity === "warning"
        ? "bg-yellow-50 border-yellow-200"
        : "bg-blue-50 border-blue-200";

  const textColor =
    severity === "error"
      ? "text-red-800"
      : severity === "warning"
        ? "text-yellow-800"
        : "text-blue-800";

  const iconColor =
    severity === "error"
      ? "text-red-500"
      : severity === "warning"
        ? "text-yellow-500"
        : "text-blue-500";

  return (
    <div className={`border rounded-lg p-4 ${bgColor} space-y-3`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          <AlertCircle className={`w-5 h-5 ${iconColor} flex-shrink-0 mt-0.5`} />
          <div className="flex-1">
            {/* Error Code */}
            <div className={`text-xs font-semibold ${textColor} opacity-75 mb-1`}>
              {error.error_code}
            </div>

            {/* Main Message */}
            <h3 className={`font-semibold ${textColor}`}>{error.message}</h3>

            {/* Details */}
            {error.details && (
              <p className={`text-sm ${textColor} opacity-75 mt-1`}>
                {error.details}
              </p>
            )}

            {/* Suggestions */}
            {error.suggestions && error.suggestions.length > 0 && (
              <div className="mt-3 space-y-2">
                <button
                  onClick={() => setShowMore(!showMore)}
                  className={`flex items-center gap-2 text-sm font-medium ${textColor} hover:opacity-75 transition-opacity`}
                >
                  <ChevronDown
                    className={`w-4 h-4 transition-transform ${
                      showMore ? "rotate-180" : ""
                    }`}
                  />
                  {showMore ? "Hide" : "Show"} suggestions ({error.suggestions.length})
                </button>

                {showMore && (
                  <ul className={`text-sm ${textColor} opacity-75 space-y-1 ml-6 list-disc`}>
                    {error.suggestions.map((suggestion, idx) => (
                      <li key={idx}>{suggestion}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Request ID for support */}
            {error.request_id && (
              <div className={`text-xs ${textColor} opacity-50 mt-2 font-mono`}>
                Request ID: {error.request_id}
              </div>
            )}
          </div>
        </div>

        {/* Close Button */}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className={`flex-shrink-0 ${textColor} hover:opacity-75 transition-opacity`}
            aria-label="Dismiss error"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Action Buttons */}
      {(onRetry || onDismiss) && (
        <div className="flex gap-2 pt-2 border-t border-current opacity-25">
          {onRetry && (
            <button
              onClick={onRetry}
              className={`flex items-center gap-2 px-3 py-2 rounded text-sm font-medium ${textColor} hover:opacity-75 transition-opacity`}
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
          )}
          {onDismiss && (
            <button
              onClick={onDismiss}
              className={`flex items-center gap-2 px-3 py-2 rounded text-sm font-medium ${textColor} hover:opacity-75 transition-opacity`}
            >
              Dismiss
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Compact inline error component
 */
interface InlineErrorProps {
  error: ApiError | null;
  onDismiss?: () => void;
}

export function InlineError({ error, onDismiss }: InlineErrorProps) {
  if (!error) return null;

  const severity = getErrorSeverity(error.error_code);
  const borderColor =
    severity === "error"
      ? "border-l-red-500"
      : severity === "warning"
        ? "border-l-yellow-500"
        : "border-l-blue-500";

  const bgColor =
    severity === "error"
      ? "bg-red-50"
      : severity === "warning"
        ? "bg-yellow-50"
        : "bg-blue-50";

  return (
    <div
      className={`border-l-4 ${borderColor} ${bgColor} p-4 rounded flex items-start justify-between gap-3`}
    >
      <div>
        <p className="font-semibold text-sm">{error.message}</p>
        {error.details && (
          <p className="text-xs opacity-75 mt-1">{error.details}</p>
        )}
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="flex-shrink-0 hover:opacity-75 transition-opacity"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
