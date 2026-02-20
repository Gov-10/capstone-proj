/**
 * Custom hook for handling API errors with user-friendly messages
 */

import { useState, useCallback } from "react";
import { ApiError, parseApiError, isRetryableError } from "@/lib/errorHandling";

interface UseApiErrorReturn {
  error: ApiError | null;
  loading: boolean;
  setError: (error: ApiError | null) => void;
  setLoading: (loading: boolean) => void;
  handleError: (response: any) => void;
  clearError: () => void;
  retry?: () => Promise<void>;
}

export function useApiError(): UseApiErrorReturn {
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);

  const handleError = useCallback((response: any) => {
    const parsedError = parseApiError(response);
    setError(parsedError);
    console.error("API Error:", parsedError);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    error,
    loading,
    setError,
    setLoading,
    handleError,
    clearError,
  };
}

/**
 * Hook for handling file upload with validation
 */
interface FileValidationError {
  isValid: boolean;
  error?: ApiError;
}

export function useFileValidation() {
  const validateFile = useCallback(
    (file: File): FileValidationError => {
      // Check file type
      if (file.type !== "application/pdf") {
        return {
          isValid: false,
          error: {
            success: false,
            error_code: "INVALID_FILE_FORMAT",
            message: "Unsupported file format",
            details: `File type '${file.type}' is not supported`,
            suggestions: [
              "Upload a PDF document",
              "Ensure the file has a .pdf extension",
              "For other file types, convert to PDF first",
            ],
          },
        };
      }

      // Check file size (50 MB limit)
      const maxSize = 50 * 1024 * 1024; // 50 MB
      if (file.size > maxSize) {
        return {
          isValid: false,
          error: {
            success: false,
            error_code: "FILE_TOO_LARGE",
            message: "File is too large",
            details: `Maximum file size is 50 MB, but your file is ${(file.size / (1024 * 1024)).toFixed(2)} MB`,
            suggestions: [
              "Try compressing the PDF",
              "Split the PDF into smaller parts",
              "Remove unnecessary images or attachments",
            ],
          },
        };
      }

      // Check for minimum file size
      const minSize = 1024; // 1 KB
      if (file.size < minSize) {
        return {
          isValid: false,
          error: {
            success: false,
            error_code: "INVALID_FILE_FORMAT",
            message: "File is too small",
            details: "The file must be at least 1 KB",
            suggestions: ["Ensure you selected the correct file"],
          },
        };
      }

      return { isValid: true };
    },
    []
  );

  return { validateFile };
}

/**
 * Hook for monitoring analysis progress
 */
interface UseProgressOptions {
  requestId?: string;
  onComplete?: () => void;
  onError?: (error: ApiError) => void;
  pollInterval?: number;
}

export function useAnalysisProgress(
  options: UseProgressOptions = {}
): {
  progress: number;
  status: string;
  currentStep: string;
  estimatedTime: number | null;
  error: ApiError | null;
  isComplete: boolean;
} {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("idle");
  const [currentStep, setCurrentStep] = useState("");
  const [estimatedTime, setEstimatedTime] = useState<number | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  const {
    requestId,
    onComplete,
    onError,
    pollInterval = 2000,
  } = options;

  // Poll progress endpoint
  const pollProgress = useCallback(async () => {
    if (!requestId) return;

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_FASTAPI_URL}/progress/${requestId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        const parsedError = parseApiError(errorData);
        setError(parsedError);
        onError?.(parsedError);
        return;
      }

      const data = await response.json();

      setProgress(data.progress_percent || 0);
      setStatus(data.status || "unknown");
      setCurrentStep(data.current_step || "Processing...");
      setEstimatedTime(data.estimated_time_remaining);

      if (data.status === "completed") {
        setIsComplete(true);
        onComplete?.();
      } else if (data.status === "failed") {
        const failError: ApiError = {
          success: false,
          error_code: data.error || "ANALYSIS_FAILED",
          message: "Analysis failed",
        };
        setError(failError);
        onError?.(failError);
      }
    } catch (err) {
      const errorResponse: ApiError = {
        success: false,
        error_code: "PROGRESS_CHECK_FAILED",
        message: "Failed to check analysis progress",
        suggestions: ["The analysis may still be processing", "Try refreshing"],
      };
      setError(errorResponse);
      onError?.(errorResponse);
    }
  }, [requestId, onComplete, onError]);

  // Setup polling
  React.useEffect(() => {
    if (!requestId) return;

    const interval = setInterval(() => {
      pollProgress();
    }, pollInterval);

    // Poll immediately
    pollProgress();

    return () => clearInterval(interval);
  }, [requestId, pollProgress, pollInterval]);

  return {
    progress,
    status,
    currentStep,
    estimatedTime,
    error,
    isComplete,
  };
}
