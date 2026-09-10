import logging

import pytest

from app.services.transfer_logging import TransferLoggingMiddleware


@pytest.mark.parametrize("fail", [False, True])
async def test_transfer_logging_counts_delivery_without_credentials(caplog, fail):
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-length", b"6")]})
        await send({"type": "http.response.body", "body": b"abc", "more_body": True})
        if fail:
            raise OSError("secret-password")
        await send({"type": "http.response.body", "body": b"def"})

    messages = []

    async def send(message):
        messages.append(message)

    scope = {"type": "http", "method": "GET", "path": "/rest/download.view", "query_string": b"p=secret-password"}
    with caplog.at_level(logging.INFO, logger="dtp_tunes.transfer"):
        if fail:
            with pytest.raises(OSError):
                await TransferLoggingMiddleware(app)(scope, None, send)
        else:
            await TransferLoggingMiddleware(app)(scope, None, send)
    assert "secret-password" not in caplog.text
    assert f"bytes_sent={3 if fail else 6}" in caplog.text
    assert f"complete={not fail}" in caplog.text
    assert b"x-request-id" in dict(messages[0]["headers"])
