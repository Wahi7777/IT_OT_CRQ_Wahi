"""S3 JSON persistence and SQS publication abstractions for Phase 5A."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol

from crq.application.serialization import dumps, loads


class ObjectNotFound(KeyError):
    pass


class ObjectConflict(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredObject:
    value: dict[str, Any]
    etag: str


class ObjectStore(Protocol):
    def get(self, key: str) -> StoredObject: ...
    def put(self, key: str, value: dict[str, Any], *, if_none_match: bool = False, if_match: str | None = None) -> str: ...


class JobQueue(Protocol):
    def send(self, value: dict[str, Any]) -> None: ...


class S3ObjectStore:
    def __init__(self, bucket: str, client: Any | None = None):
        if not bucket:
            raise ValueError("bucket is required")
        if client is None:
            import boto3
            client = boto3.client("s3")
        self.bucket = bucket
        self.client = client

    def get(self, key: str) -> StoredObject:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            code = str(getattr(exc, "response", {}).get("Error", {}).get("Code", ""))
            if code in {"NoSuchKey", "404", "NotFound"}:
                raise ObjectNotFound(key) from exc
            raise
        value = loads(response["Body"].read())
        if not isinstance(value, dict):
            raise ValueError("persisted JSON object is invalid")
        return StoredObject(value=value, etag=str(response.get("ETag", "")).strip('"'))

    def put(self, key: str, value: dict[str, Any], *, if_none_match: bool = False, if_match: str | None = None) -> str:
        arguments: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": dumps(value).encode("utf-8"),
            "ContentType": "application/json",
            "ServerSideEncryption": "AES256",
        }
        if if_none_match:
            arguments["IfNoneMatch"] = "*"
        if if_match:
            arguments["IfMatch"] = if_match
        try:
            response = self.client.put_object(**arguments)
        except Exception as exc:
            code = str(getattr(exc, "response", {}).get("Error", {}).get("Code", ""))
            status = getattr(exc, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in {"PreconditionFailed", "ConditionalRequestConflict", "412", "409"} or status in {409, 412}:
                raise ObjectConflict(key) from exc
            raise
        return str(response.get("ETag", "")).strip('"')


class SQSJobQueue:
    def __init__(self, queue_url: str, client: Any | None = None):
        if not queue_url:
            raise ValueError("queue_url is required")
        if client is None:
            import boto3
            client = boto3.client("sqs")
        self.queue_url = queue_url
        self.client = client

    def send(self, value: dict[str, Any]) -> None:
        self.client.send_message(QueueUrl=self.queue_url, MessageBody=dumps(value))


class MemoryObjectStore:
    """Deterministic test store with S3-like conditional writes."""

    def __init__(self):
        self.objects: dict[str, StoredObject] = {}

    def get(self, key: str) -> StoredObject:
        if key not in self.objects:
            raise ObjectNotFound(key)
        stored = self.objects[key]
        return StoredObject(value=loads(dumps(stored.value)), etag=stored.etag)

    def put(self, key: str, value: dict[str, Any], *, if_none_match: bool = False, if_match: str | None = None) -> str:
        existing = self.objects.get(key)
        if if_none_match and existing is not None:
            raise ObjectConflict(key)
        if if_match is not None and (existing is None or existing.etag != if_match):
            raise ObjectConflict(key)
        body = dumps(value)
        etag = hashlib.md5(body.encode("utf-8"), usedforsecurity=False).hexdigest()  # nosec B324
        self.objects[key] = StoredObject(value=loads(body), etag=etag)
        return etag


class MemoryJobQueue:
    def __init__(self):
        self.messages: list[dict[str, Any]] = []

    def send(self, value: dict[str, Any]) -> None:
        self.messages.append(loads(dumps(value)))
