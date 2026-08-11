"""Stable job-platform exceptions used by handlers and control-plane adapters."""

from __future__ import annotations


class JobPlatformError(Exception):
    """Base class for expected job-platform failures."""

    code = "job_platform_error"


class UnknownJobHandlerError(JobPlatformError):
    code = "unknown_job_handler"

    def __init__(self, name: str, version: int) -> None:
        super().__init__(f"Unknown job handler: {name}@{version}")
        self.name = name
        self.version = version


class JobPayloadTooLargeError(JobPlatformError):
    code = "job_payload_too_large"


class JobResultTooLargeError(JobPlatformError):
    code = "job_result_too_large"


class JobProgressTooLargeError(JobPlatformError):
    code = "job_progress_too_large"


class JobEventMetadataTooLargeError(JobPlatformError):
    code = "job_event_metadata_too_large"


class JobSecretMaterialError(JobPlatformError):
    code = "job_secret_material"


class JobIdempotencyConflictError(JobPlatformError):
    code = "job_idempotency_conflict"


class JobQueueNotFoundError(JobPlatformError):
    code = "job_queue_not_found"


class JobCursorError(JobPlatformError):
    code = "invalid_job_cursor"


class JobNotFoundError(JobPlatformError):
    code = "job_not_found"


class RetryableJobError(JobPlatformError):
    code = "job_retryable_failure"


class BlockedJobError(JobPlatformError):
    code = "job_blocked"


class PermanentJobError(JobPlatformError):
    code = "job_permanent_failure"


class JobCancelled(JobPlatformError):
    code = "job_cancelled"
