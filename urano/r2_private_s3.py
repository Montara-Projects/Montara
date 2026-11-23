"""Private R2 S3 object transport; never import into public browser assets.

Not wired to MAIN/Worker. Inject an authorized server-side S3 client; its secret
keys are obtained exclusively by the service configuration and are never
returned to the user. Bucket credentials must be scoped to the pilot bucket.
The object authorization happens in r2_owner_bridge before calling this class.
"""
from __future__ import annotations

import io
import re
from typing import Any

class R2StorageConfigurationError(ValueError):
    pass


class PrivateR2S3Storage:
    """Implements the synthetic bridge protocol against the private S3 API.

    Production large files must use resumable multipart, not this 1-MiB fixture.
    """
    def __init__(self, client: Any, bucket: str):
        if not isinstance(bucket, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,61}[a-z0-9]', bucket):
            raise R2StorageConfigurationError('invalid private bucket')
        self._client = client
        self._bucket = bucket

    @staticmethod
    def _key(key: str) -> str:
        if not isinstance(key, str) or not re.fullmatch(r'pilot/(?:fergardel|amehc|t4t)/[0-9a-f]{32}', key):
            raise R2StorageConfigurationError('invalid private object key')
        return key

    def put(self, key: str, content: bytes) -> None:
        self._key(key)
        if not isinstance(content, bytes) or not 0 < len(content) <= 1024 * 1024:
            raise R2StorageConfigurationError('only bounded synthetic fixture supported')
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content,
                                ContentType='application/octet-stream',
                                Metadata={'sha256': __import__('hashlib').sha256(content).hexdigest()})

    def get(self, key: str) -> bytes | None:
        self._key(key)
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            # Do not hide transport/authentication errors as missing objects.
            response_code = getattr(exc, 'response', {}).get('Error', {}).get('Code')
            if response_code in ('NoSuchKey', '404'):
                return None
            raise
        body = response['Body']
        # A bounded fixture must never read unbounded server-selected content.
        length = response.get('ContentLength')
        if length is not None and (type(length) is not int or length > 1024*1024):
            raise R2StorageConfigurationError('private object too large for synthetic readback')
        result = body.read(1024*1024+1)
        if len(result) > 1024*1024:
            raise R2StorageConfigurationError('private object too large for synthetic readback')
        return result

    def delete(self, key: str) -> None:
        self._key(key)
        self._client.delete_object(Bucket=self._bucket, Key=key)


def build_private_r2_s3_client(*, account_id: str, access_key_id: str, secret_access_key: str):
    """Server-only factory. Requires optional boto3 dependency in deploy image.

    Credentials must come from Worker secret bindings/secret manager, never
    query strings, request bodies, URLs, HTML, logs or repository files.
    """
    if not isinstance(account_id, str) or not re.fullmatch(r'[a-f0-9]{32}', account_id):
        raise R2StorageConfigurationError('invalid Cloudflare account')
    if not access_key_id or not secret_access_key:
        raise R2StorageConfigurationError('missing service-only credentials')
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise R2StorageConfigurationError('server boto3 dependency unavailable') from exc
    return boto3.client('s3', endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key,
        region_name='auto', config=Config(signature_version='s3v4',
                                           retries={'mode':'standard','max_attempts':3}))
