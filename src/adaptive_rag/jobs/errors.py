"""Stable job-platform exceptions used by handlers and control-plane adapters."""

from __future__ import annotations


class JobPlatformError(Exception):
    """Base class for expected job-platform failures."""

    code = "job_platform_error"
    default_public_message = "job operation failed; see trace ID"

    def __init__(
        self,
        *args: object,
        public_message: str | None = None,
    ) -> None:
        super().__init__(*args)
        self.public_message = public_message or self.default_public_message


class UnknownJobHandlerError(JobPlatformError):
    code = "unknown_job_handler"

    def __init__(self, name: str, version: int) -> None:
        super().__init__(f"Unknown job handler: {name}@{version}")
        self.name = name
        self.version = version


class JobPayloadTooLargeError(JobPlatformError):
    code = "job_payload_too_large"


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


class JobStateConflictError(JobPlatformError):
    code = "job_state_conflict"


class RetryableJobError(JobPlatformError):
    code = "job_retryable_failure"
    default_public_message = "job failed and will be retried; see trace ID"


class BlockedJobError(JobPlatformError):
    code = "job_blocked"
    default_public_message = "job is blocked; see trace ID"


class PermanentJobError(JobPlatformError):
    code = "job_permanent_failure"
    default_public_message = "job failed permanently; see trace ID"


class JobResultTooLargeError(PermanentJobError):
    code = "job_result_too_large"
    default_public_message = "job result exceeded the allowed size"


class InvalidJobResultError(PermanentJobError):
    code = "invalid_job_result"
    default_public_message = "job result is not valid JSON"


class JobCancelled(JobPlatformError):
    code = "job_cancelled"
    default_public_message = "job cancellation confirmed"
