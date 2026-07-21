"""OpenSubsonic response envelopes: JSON/XML serialization and error codes.

Reference: https://opensubsonic.netlify.app/docs/api-reference/
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import Request
from fastapi.responses import Response

API_VERSION = "1.16.1"
SERVER_VERSION = "0.1.0"
SERVER_NAME = "dtp-tunes"
OPEN_SUBSONIC_EXTENSIONS = [
    {"name": "transcodeOffset", "versions": [1]},
    {"name": "formPost", "versions": [1]},
    {"name": "apiKeyAuthentication", "versions": [1]},
]


class SubsonicError:
    GENERIC = 0
    MISSING_PARAMETER = 10
    INCOMPATIBLE_CLIENT = 20
    INCOMPATIBLE_SERVER = 30
    WRONG_CREDENTIALS = 40
    TOKEN_AUTH_NOT_SUPPORTED = 41
    NOT_AUTHORIZED = 50
    NOT_FOUND = 70


def _wants_xml(request: Request, params: dict) -> bool:
    fmt = params.get("f", "json")
    return fmt.lower() == "xml"


def ok_envelope(payload: dict | None = None) -> dict:
    body = {"status": "ok", "version": API_VERSION, "type": SERVER_NAME, "serverVersion": SERVER_VERSION, "openSubsonic": True}
    if payload:
        body.update(payload)
    return {"subsonic-response": body}


def error_envelope(code: int, message: str) -> dict:
    return {
        "subsonic-response": {
            "status": "failed",
            "version": API_VERSION,
            "type": SERVER_NAME,
            "serverVersion": SERVER_VERSION,
            "openSubsonic": True,
            "error": {"code": code, "message": message},
        }
    }


def _dict_to_xml(tag: str, data, parent: Element | None = None) -> Element:
    element = Element(tag) if parent is None else SubElement(parent, tag)
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                if isinstance(value, list):
                    for item in value:
                        _dict_to_xml(key, item, element)
                else:
                    _dict_to_xml(key, value, element)
            else:
                element.set(key, _xml_str(value))
    return element


def _xml_str(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def render_envelope(request: Request, params: dict, envelope: dict) -> Response:
    """Render either JSON (default) or Subsonic-style XML based on the `f` query param."""
    if _wants_xml(request, params):
        inner = envelope["subsonic-response"]
        root = Element(
            "subsonic-response",
            attrib={
                "xmlns": "http://subsonic.org/restapi",
                "status": inner["status"],
                "version": inner["version"],
                "type": inner["type"],
                "serverVersion": inner["serverVersion"],
                "openSubsonic": "true",
            },
        )
        for key, value in inner.items():
            if key in {"status", "version", "type", "serverVersion", "openSubsonic"}:
                continue
            if isinstance(value, list):
                for item in value:
                    _dict_to_xml(key, item, root)
            else:
                _dict_to_xml(key, value, root)
        xml_bytes = b'<?xml version="1.0" encoding="UTF-8"?>' + tostring(root)
        return Response(content=xml_bytes, media_type="text/xml; charset=utf-8")

    import orjson

    return Response(content=orjson.dumps(envelope), media_type="application/json")
