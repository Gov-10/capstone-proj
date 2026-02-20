# Better Error Handling Implementation

This document describes the comprehensive error handling improvements added to the Legal Summarizer project.

## Overview

The error handling has been enhanced across all three services (Django Backend, FastAPI Backend, and NextJS Frontend) to provide:

- **Detailed error messages** - Users get specific information about what went wrong
- **Actionable suggestions** - Each error includes suggestions to fix the issue
- **Progress tracking** - Users can monitor document analysis progress in real-time
- **User-friendly UI components** - Error and progress components with clear visual feedback
- **Structured error responses** - Consistent error format across all APIs
- **Request tracking** - Monitor status of long-running operations with request IDs

## Backend Changes

### FastAPI Error Handling (`fastapi_agents/errors.py`, `fastapi_agents/progress.py`)

#### Error Classes

- **`ErrorResponse`** - Standardized error response with code, message, details, and suggestions
- **`DocumentValidationError`** - File validation failures (format, size, content)
- **`FileProcessingError`** - PDF processing failures
- **`AnalysisError`** - Analysis processing failures
- **`AuthenticationError`** - Authentication failures

#### Error Codes

```
INVALID_FILE_FORMAT      - File format not supported
FILE_TOO_LARGE          - File exceeds size limit
FILE_CORRUPTED          - File is corrupted or invalid
NO_TEXT_EXTRACTED       - PDF has no readable text
ANALYSIS_FAILED         - Analysis processing failed
AUTH_FAILED             - Authentication failed
S3_ERROR                - S3 communication failed
TIMEOUT                 - Operation timed out
RATE_LIMITED            - Request rate limit exceeded
INVALID_REQUEST         - Invalid request format
INTERNAL_ERROR          - Unexpected server error
```

#### Progress Tracking

New modules added:
- `ProcessingStatus` enum with states: queued, validating, extracting_text, chunking, summarizing, analyzing, caching, completed, failed
- `RequestTracker` class to monitor long-running analysis operations
- `estimate_processing_time()` function to calculate processing time based on file size

#### New Endpoints

- **`GET /progress/{request_id}`** - Get real-time progress of document analysis
- **`GET /health`** - Health check endpoint to verify service availability

#### Enhanced `/status` Endpoint

The main analysis endpoint now:
- Creates request IDs for tracking
- Validates document format and size
- Provides detailed error messages at each step
- Updates progress in real-time
- Catches and handles errors gracefully
- Logs all operations for debugging

### Django Error Handling (`django_back/backapp/errors.py`, `validation.py`)

#### New Modules

**`errors.py`** - Error handling utilities
- `ApiError` model for consistent responses
- `raise_validation_error()` - Validation error handler
- `raise_s3_error()` - S3-related error handler
- `raise_pubsub_error()` - Pub/Sub-related error handler
- `raise_internal_error()` - Internal error handler

**`validation.py`** - File validation utilities
- `validate_file_format()` - Check if file is PDF
- `validate_content_type()` - Check MIME type
- `validate_file_size()` - Check file size constraints
- `get_format_suggestions()` - Suggestions for format issues
- `get_size_suggestions()` - Suggestions for size issues

#### Enhanced `/get-upload-url` Endpoint

Now includes comprehensive validation:
- File format validation (PDF only)
- Content type validation
- Filename length and character validation
- File size validation
- S3 connection checks
- Pub/Sub availability checks
- Detailed error messages with actionable suggestions

#### Schema Changes

Updated `schema.py` with `ErrorOut` for consistent error responses

## Frontend Changes

### Error Handling Utilities (`src/lib/errorHandling.ts`)

```typescript
// Parse API errors into structured format
parseApiError(response: any): ApiError

// Check if error is retryable
isRetryableError(errorCode: string): boolean

// Check if error is user input related
isUserInputError(errorCode: string): boolean

// Get error severity for styling
getErrorSeverity(errorCode: string): "error" | "warning" | "info"

// Format progress status for display
formatProgressStatus(status: string): string

// Format file size (e.g., "5.2 MB")
formatFileSize(bytes: number): string

// Format seconds to readable time (e.g., "2m 30s")
formatSeconds(seconds: number): string
```

### Custom Hooks (`src/hooks/useApiError.ts`)

#### `useApiError()`
Hook for managing API errors
```typescript
const { error, loading, handleError, clearError, setError, setLoading } = useApiError();
```

#### `useFileValidation()`
Hook for file upload validation
```typescript
const { validateFile } = useFileValidation();
const validation = validateFile(file);
```

#### `useAnalysisProgress()`
Hook for monitoring analysis progress
```typescript
const { progress, status, currentStep, estimatedTime, error, isComplete } = useAnalysisProgress({
  requestId: "uuid",
  onComplete: () => {},
  onError: (error) => {},
  pollInterval: 2000
});
```

### UI Components

#### `ErrorDisplay.tsx`
Full error display component with:
- Error code and message
- Detailed explanation
- Expandable suggestions list
- Request ID for support
- Retry and dismiss buttons
- Color-coded by severity (error, warning, info)

#### `InlineError.tsx`
Compact inline error component for forms

#### `ProgressDisplay.tsx`
Progress bar component showing:
- Current status
- Progress percentage
- Estimated time remaining
- Chunk processing progress
- Animated progress bar
- Status-specific icons and colors

#### `UploadProgress.tsx`
Upload progress component showing:
- File name and size
- Upload progress bar
- Pending status indicator

## Usage Examples

### Frontend - File Upload with Error Handling

```typescript
// In your dashboard/upload component
const { error, setError, clearError } = useApiError();
const { validateFile } = useFileValidation();

const handleFileSelect = (file: File) => {
  const validation = validateFile(file);
  if (!validation.isValid) {
    setError(validation.error);
    return;
  }

  // Proceed with upload
};
```

### Frontend - Monitoring Analysis Progress

```typescript
const {
  progress,
  status,
  currentStep,
  estimatedTime,
  error,
  isComplete
} = useAnalysisProgress({
  requestId: analysisRequestId,
  onComplete: () => {
    // Handle completion
  },
  onError: (error) => {
    // Handle error
  }
});

return (
  <>
    {error && <ErrorDisplay error={error} onDismiss={clearError} />}
    <ProgressDisplay
      progress={progress}
      status={status}
      currentStep={currentStep}
      estimatedTime={estimatedTime}
    />
  </>
);
```

### FastAPI - Document Analysis

```python
# The /status endpoint now handles errors gracefully
# Returns detailed error response on failure

# Example error response:
{
  "success": false,
  "error_code": "FILE_TOO_LARGE",
  "message": "File is too large (maximum 50.0 MB)",
  "details": "File size: 65.34 MB",
  "suggestions": [
    "Maximum file size: 50.0 MB",
    "Try compressing the PDF or splitting it into smaller parts",
    "Ensure there are no extra images or embedded media"
  ],
  "request_id": "uuid-here"
}
```

### Django - Upload URL Generation

```python
# The /get-upload-url endpoint now validates comprehensively
# Returns helpful error messages for invalid requests

# Example error response:
{
  "success": false,
  "error_code": "INVALID_FILE_FORMAT",
  "message": "Unsupported file format",
  "details": "File 'document.docx' has an unsupported extension",
  "suggestions": [
    "Supported formats: .pdf",
    "Ensure the PDF is not password protected",
    "Ensure the PDF contains readable text, not just images"
  ]
}
```

## File Structure

```
Legal-Summarizer/
├── fastapi_agents/
│   ├── errors.py              # Error handling classes and utilities
│   ├── progress.py            # Progress tracking utilities
│   └── main.py                # Updated with comprehensive error handling
│
├── django_back/backapp/
│   ├── errors.py              # Django error handling utilities
│   ├── validation.py          # File validation utilities
│   ├── api.py                 # Updated endpoints with error handling
│   └── schema.py              # Updated with ErrorOut schema
│
└── front/src/
    ├── lib/
    │   └── errorHandling.ts   # Error parsing and formatting utilities
    ├── hooks/
    │   └── useApiError.ts      # Custom error/file/progress hooks
    └── components/
        ├── ErrorDisplay.tsx    # Error display component
        └── ProgressDisplay.tsx # Progress tracking component
```

## Benefits

1. **Better User Experience**
   - Users understand what went wrong
   - Clear suggestions on how to fix issues
   - Real-time progress feedback

2. **Easier Debugging**
   - Request IDs for support
   - Detailed server logs
   - Error codes for categorization

3. **Improved Reliability**
   - Graceful error handling
   - Retryable error detection
   - Health checks for external services

4. **Better Maintenance**
   - Consistent error format
   - Centralized error utilities
   - Clear separation of concerns

## Testing Error Handling

### Manual Testing

1. **File Upload Validation**
   - Upload non-PDF file → Should get INVALID_FILE_FORMAT error
   - Upload file > 50MB → Should get FILE_TOO_LARGE error
   - Upload empty file → Should get FILE_TOO_SMALL error

2. **Progress Tracking**
   - Upload valid PDF
   - Check `/progress/{request_id}` endpoint
   - Should see real-time progress updates

3. **Error Recovery**
   - Trigger an error
   - Click "Try Again" button
   - Should retry the operation

### Automated Testing (TODO)

```bash
# Run error handling tests
pytest tests/test_error_handling.py

# Test file validation
pytest tests/test_file_validation.py

# Test progress tracking
pytest tests/test_progress_tracking.py
```

## Future Improvements

1. **Monitoring & Observability**
   - Add Prometheus metrics
   - Grafana dashboards
   - Error tracking (Sentry)

2. **Retry Mechanisms**
   - Automatic retry with exponential backoff
   - User-triggered retry
   - Circuit breaker pattern

3. **Audit Logging**
   - Track all errors
   - User action history
   - API call logging

4. **Multi-language Support**
   - Translate error messages
   - Locale-specific suggestions
   - RTL/LTR support

5. **Advanced Diagnostics**
   - Error rate monitoring
   - Performance metrics
   - User feedback collection
