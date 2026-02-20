/**
 * Progress display component for file uploads and analysis
 */

"use client";

import React from "react";
import { formatSeconds, formatProgressStatus } from "@/lib/errorHandling";
import { CheckCircle2, Loader2, AlertCircle } from "lucide-react";

interface ProgressDisplayProps {
  progress: number; // 0-100
  status:
    | "queued"
    | "validating"
    | "extracting_text"
    | "chunking"
    | "summarizing"
    | "analyzing"
    | "caching"
    | "completed"
    | "failed"
    | "uploading";
  currentStep: string;
  estimatedTime?: number | null;
  chunksProcessed?: number;
  chunksTotal?: number;
}

export function ProgressDisplay({
  progress,
  status,
  currentStep,
  estimatedTime,
  chunksProcessed,
  chunksTotal,
}: ProgressDisplayProps) {
  const isComplete = status === "completed";
  const isFailed = status === "failed";

  return (
    <div className="space-y-3">
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isComplete ? (
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            ) : isFailed ? (
              <AlertCircle className="w-5 h-5 text-red-500" />
            ) : (
              <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
            )}
            <div>
              <p className="font-semibold text-gray-900">
                {formatProgressStatus(status)}
              </p>
              <p className="text-sm text-gray-600">{currentStep}</p>
            </div>
          </div>
          <div className="text-right">
            <p className="font-semibold text-lg text-gray-900">{progress}%</p>
            {estimatedTime && estimatedTime > 0 && (
              <p className="text-xs text-gray-600">
                {formatSeconds(estimatedTime)} remaining
              </p>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              isComplete
                ? "bg-green-500"
                : isFailed
                  ? "bg-red-500"
                  : "bg-blue-500"
            }`}
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      </div>

      {/* Chunk Progress */}
      {chunksTotal && chunksTotal > 0 && (
        <div className="text-sm text-gray-600">
          Processing section {chunksProcessed} of {chunksTotal}
        </div>
      )}

      {/* Status Message */}
      {isFailed && (
        <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          Analysis failed. Please check the error message above for details.
        </div>
      )}

      {isComplete && (
        <div className="p-3 bg-green-50 border border-green-200 rounded text-sm text-green-700">
          Analysis complete! Your results are ready.
        </div>
      )}
    </div>
  );
}

/**
 * Upload progress component with file info
 */
interface UploadProgressProps {
  fileName: string;
  fileSize: number;
  uploadProgress: number;
  isUploading: boolean;
  isPending?: boolean;
}

export function UploadProgress({
  fileName,
  fileSize,
  uploadProgress,
  isUploading,
  isPending = false,
}: UploadProgressProps) {
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        {isUploading || isPending ? (
          <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
        ) : (
          <CheckCircle2 className="w-5 h-5 text-green-500" />
        )}
        <div className="flex-1">
          <p className="font-semibold text-gray-900 truncate">{fileName}</p>
          <p className="text-sm text-gray-600">{formatBytes(fileSize)}</p>
        </div>
        <div className="text-right">
          <p className="font-semibold text-gray-900">{uploadProgress}%</p>
        </div>
      </div>

      {/* Upload Progress Bar */}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className="h-2 rounded-full bg-blue-500 transition-all duration-300"
          style={{ width: `${uploadProgress}%` }}
        />
      </div>

      {isPending && (
        <p className="text-sm text-gray-600 text-center">
          Waiting for server to process your document...
        </p>
      )}
    </div>
  );
}
