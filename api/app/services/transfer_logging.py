"""Credential-free ASGI diagnostics for Subsonic requests, including body delivery."""

import logging
import time
import uuid

logger = logging.getLogger("dtp_tunes.transfer")


class TransferLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/rest/"):
            return await self.app(scope, receive, send)
        request_id = uuid.uuid4().hex
        scope.setdefault("state", {})["transfer_id"] = request_id
        started = time.monotonic()
        status, sent, complete = None, 0, False
        expected, content_type = None, None
        logger.info("request_started request_id=%s method=%s path=%r", request_id, scope["method"], scope["path"])

        async def traced_send(message):
            nonlocal status, sent, complete, expected, content_type
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                status = message["status"]
                expected = headers.get(b"content-length")
                content_type = headers.get(b"content-type")
                message = {**message, "headers": [*message.get("headers", []), (b"x-request-id", request_id.encode())]}
            await send(message)
            if message["type"] == "http.response.body":
                sent += len(message.get("body", b""))
                complete = not message.get("more_body", False)

        try:
            await self.app(scope, receive, traced_send)
        except BaseException as exc:
            # Exception strings and URLs can contain credentials. Log only the type.
            logger.warning("request_failed request_id=%s error_type=%s", request_id, type(exc).__name__)
            raise
        finally:
            logger.info(
                "request_finished request_id=%s status=%s bytes_sent=%s expected_bytes=%r content_type=%r complete=%s elapsed_ms=%.1f",
                request_id, status, sent, expected, content_type, complete,
                (time.monotonic() - started) * 1000,
            )
