/**
 * Error handling utilities for the frontend
 */

export interface ApiError {
  success: boolean;
  error_code: string;
  message: string;
  details?: string;
  suggestions?: string[];
  timestamp?: string;
  request_id?: string;
}

export interface ProgressUpdate {
  request_id: string;
  status:
    | "queued"
    | "validating"
    | "extracting_text"
    | "chunking"
    | "summarizing"
    | "analyzing"
    | "caching"
    | "completed"
    | "failed";
  progress_percent: number;
  current_step: string;
  estimated_time_remaining?: number;
  chunks_processed?: number;
  chunks_total?: number;
  error?: string;
}

/**
 * Parse API error response with fallback
 */
export function parseApiError(response: any): ApiError {
  // Handle detailed error response
  if (response?.error_code && response?.message) {
    return {
      success: false,
      error_code: response.error_code,
      message: response.message,
      details: response.details,
      suggestions: response.suggestions || [],
      timestamp: response.timestamp,
      request_id: response.request_id,
    };
  }

  // Handle standard HTTP error
  if (response?.detail) {
    const detail = response.detail;
    if (typeof detail === "string") {
      return {
        success: false,
        error_code: response.status || "UNKNOWN_ERROR",
        message: detail,
      };
    }
    if (typeof detail === "object") {
      return {
        success: false,
        error_code: detail.error_code || "UNKNOWN_ERROR",
        message: detail.message || "An error occurred",
        details: detail.details,
        suggestions: detail.suggestions,
      };
    }
  }

  // Fallback for unknown errors
  return {
    success: false,
    error_code: "UNKNOWN_ERROR",
    message: "An unexpected error occurred",
    suggestions: ["Try again later", "If the problem persists, contact support"],
  };
}

/**
 * Format human-readable file size
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 Bytes";

  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

/**
 * Format time in seconds to human-readable format
 */
export function formatSeconds(seconds: number | null | undefined): string {
  if (!seconds || seconds < 0) return "Calculating...";

  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  return `${hours}h ${remainingMinutes}m`;
}

/**
 * Check if error is retryable
 */
export function isRetryableError(errorCode: string): boolean {
  const retryableErrors = [
    "TIMEOUT",
    "ANALYSIS_FAILED",
    "S3_ERROR",
    "PUBSUB_ERROR",
    "INVALID_REQUEST",
  ];
  return retryableErrors.includes(errorCode);
}

/**
 * Check if error is due to user input
 */
export function isUserInputError(errorCode: string): boolean {
  const userErrors = [
    "INVALID_FILE_FORMAT",
    "FILE_TOO_LARGE",
    "NO_TEXT_EXTRACTED",
    "VALIDATION_ERROR",
  ];
  return userErrors.includes(errorCode);
}

/**
 * Get error severity for UI styling
 */
export function getErrorSeverity(
  errorCode: string
): "error" | "warning" | "info" {
  const criticalErrors = [
    "AUTH_FAILED",
    "DATABASE_ERROR",
    "INTERNAL_ERROR",
  ];

  if (criticalErrors.includes(errorCode)) {
    return "error";
  }

  const warningErrors = [
    "TIMEOUT",
    "RATE_LIMITED",
    "S3_ERROR",
    "PUBSUB_ERROR",
  ];

  if (warningErrors.includes(errorCode)) {
    return "warning";
  }

  return "info";
}

/**
 * Format progress status to human-readable text
 */
export function formatProgressStatus(status: string): string {
  const statusMap: Record<string, string> = {
    queued: "Queued for processing",
    validating: "Validating document",
    extracting_text: "Extracting text from document",
    chunking: "Preparing document sections",
    summarizing: "Analyzing document content",
    analyzing: "Performing legal analysis",
    caching: "Saving results",
    completed: "Analysis complete",
    failed: "Analysis failed",
  };

  return statusMap[status] || status;
}
