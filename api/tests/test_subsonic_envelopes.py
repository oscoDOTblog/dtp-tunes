"""Tests for OpenSubsonic JSON/XML envelope building and error codes."""

from __future__ import annotations

import orjson
from starlette.requests import Request

from app.services.subsonic_format import SubsonicError, error_envelope, ok_envelope, render_envelope


def _fake_request() -> Request:
    scope = {"type": "http", "method": "GET", "headers": [], "query_string": b""}
    return Request(scope)


def test_ok_envelope_shape():
    envelope = ok_envelope()
    body = envelope["subsonic-response"]
    assert body["status"] == "ok"
    assert body["openSubsonic"] is True
    assert "version" in body


def test_ok_envelope_merges_payload():
    envelope = ok_envelope({"license": {"valid": True}})
    assert envelope["subsonic-response"]["license"] == {"valid": True}


def test_error_envelope_shape():
    envelope = error_envelope(SubsonicError.WRONG_CREDENTIALS, "Wrong username or password")
    body = envelope["subsonic-response"]
    assert body["status"] == "failed"
    assert body["error"]["code"] == 40
    assert body["error"]["message"] == "Wrong username or password"


def test_render_envelope_defaults_to_json():
    envelope = ok_envelope({"foo": "bar"})
    response = render_envelope(_fake_request(), {}, envelope)
    assert response.media_type == "application/json"
    parsed = orjson.loads(response.body)
    assert parsed["subsonic-response"]["foo"] == "bar"


def test_render_envelope_xml_format():
    envelope = ok_envelope()
    response = render_envelope(_fake_request(), {"f": "xml"}, envelope)
    assert response.media_type == "text/xml; charset=utf-8"
    xml_text = response.body.decode("utf-8")
    assert '<subsonic-response' in xml_text
    assert 'status="ok"' in xml_text
    assert 'openSubsonic="true"' in xml_text


def test_render_envelope_xml_nests_list_payloads():
    envelope = ok_envelope({"albumList2": {"album": [{"id": "a1", "name": "Album One"}, {"id": "a2", "name": "Album Two"}]}})
    response = render_envelope(_fake_request(), {"f": "xml"}, envelope)
    xml_text = response.body.decode("utf-8")
    assert xml_text.count("<album ") == 2
    assert 'id="a1"' in xml_text
    assert 'id="a2"' in xml_text


def test_render_envelope_xml_error_status():
    envelope = error_envelope(SubsonicError.NOT_FOUND, "Song not found")
    response = render_envelope(_fake_request(), {"f": "xml"}, envelope)
    xml_text = response.body.decode("utf-8")
    assert 'status="failed"' in xml_text
    assert 'code="70"' in xml_text
