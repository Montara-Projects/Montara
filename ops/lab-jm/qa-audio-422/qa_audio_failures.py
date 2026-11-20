"""Conservative LAB-JM QA audio failure labels. No media/path/error strings leave QA."""
from __future__ import annotations
import errno

# These OS failures are known to be transient in the proxy preparation phase.
_TEMPORARY_IO = {errno.EAGAIN, errno.EINTR, errno.EBUSY, errno.ETIMEDOUT,
                 errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE}


def classify_audio_failure(exc: Exception) -> tuple[int, dict]:
    """Return safe HTTP status/metadata; default to non-retryable.

    A client may retry ONLY when both code and retryable are explicitly present;
    authentication, malformed uploads, resource exhaustion and unknown runtime
    failures must never be replayed automatically.
    """
    if isinstance(exc, PermissionError):
        return 403, {'code':'AUDIO_AUTH_DENIED','retryable':False}
    if isinstance(exc, FileNotFoundError):
        return 404, {'code':'AUDIO_ORIGINAL_MISSING','retryable':False}
    if isinstance(exc, ValueError):
        return 422, {'code':'AUDIO_INVALID_REQUEST','retryable':False}
    if isinstance(exc, TimeoutError):
        return 503, {'code':'AUDIO_TEMPORARY_TIMEOUT','retryable':True}
    if isinstance(exc, OSError) and exc.errno in _TEMPORARY_IO:
        return 503, {'code':'AUDIO_TEMPORARY_IO','retryable':True}
    if isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
        return 507, {'code':'AUDIO_INSUFFICIENT_STORAGE','retryable':False}
    if isinstance(exc, OSError):
        return 422, {'code':'AUDIO_IO_FAILED','retryable':False}
    if isinstance(exc, RuntimeError):
        return 422, {'code':'AUDIO_PREPARATION_FAILED','retryable':False}
    return 422, {'code':'AUDIO_FAILED','retryable':False}


def safe_audio_error(exc: Exception) -> tuple[int, dict]:
    status, classified = classify_audio_failure(exc)
    return status, {'error':'Companion could not prepare this audio track.', **classified}
