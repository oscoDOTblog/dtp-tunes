"""Helpers for reading OpenSubsonic parameters from GET query or POST form bodies."""

from __future__ import annotations

from fastapi import Request
from starlette.datastructures import FormData, QueryParams


class SubsonicParams:
    def __init__(self, query: QueryParams, form: FormData | None):
        self._query = query
        self._form = form

    def get(self, name: str, default: str | None = None) -> str | None:
        if self._form is not None and name in self._form:
            value = self._form.get(name)
            return str(value) if value is not None else default
        return self._query.get(name, default)

    def get_list(self, name: str) -> list[str]:
        if self._form is not None and name in self._form:
            return [str(v) for v in self._form.getlist(name)]
        return self._query.getlist(name)

    def get_int(self, name: str, default: int | None = None) -> int | None:
        value = self.get(name)
        if value is None or value == "":
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def get_bool(self, name: str, default: bool = False) -> bool:
        value = self.get(name)
        if value is None:
            return default
        return value.lower() in {"true", "1", "yes"}

    def as_dict(self) -> dict:
        merged: dict = {}
        for key in self._query.keys():
            merged[key] = self._query.get(key)
        if self._form is not None:
            for key in self._form.keys():
                merged[key] = self._form.get(key)
        return merged


async def parse_params(request: Request) -> SubsonicParams:
    form: FormData | None = None
    if request.method == "POST":
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
    return SubsonicParams(request.query_params, form)
