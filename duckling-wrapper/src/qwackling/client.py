from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests


_UNSET = object()

_CONFIG_HELP: dict[str, dict[str, Any]] = {
    "host": {
        "default": "127.0.0.1",
        "type": "str",
        "applies_to": ["parse", "start_server"],
        "description": "Host where Duckling is reachable over HTTP.",
    },
    "port": {
        "default": 8000,
        "type": "int",
        "applies_to": ["parse", "start_server"],
        "description": "Port where Duckling listens and where a managed local process will be started.",
    },
    "stack_path": {
        "default": "stack",
        "type": "str",
        "applies_to": ["start_server"],
        "description": "Executable name or absolute path for the Haskell stack command.",
    },
    "locale": {
        "default": "en_US",
        "type": "str",
        "applies_to": ["parse"],
        "description": "Default locale sent with each parse request.",
    },
    "lang": {
        "default": None,
        "type": "str | None",
        "applies_to": ["parse"],
        "description": "Optional explicit language sent to Duckling when set.",
    },
    "dims": {
        "default": None,
        "type": "list[str] | None",
        "applies_to": ["parse"],
        "description": "Optional Duckling dimensions list such as ['time']; omitted when None.",
    },
    "latent": {
        "default": False,
        "type": "bool",
        "applies_to": ["parse"],
        "description": "Whether latent Duckling results should be included.",
    },
    "tz": {
        "default": None,
        "type": "str | None",
        "applies_to": ["parse"],
        "description": "Optional IANA timezone such as UTC or Asia/Kolkata.",
    },
    "reftime": {
        "default": None,
        "type": "int | None",
        "applies_to": ["parse"],
        "description": "Optional Unix epoch milliseconds reference time used for relative expressions.",
    },
    "request_timeout": {
        "default": 10.0,
        "type": "float",
        "applies_to": ["parse", "is_server_ready"],
        "description": "Timeout in seconds for HTTP requests to Duckling.",
    },
    "startup_retries": {
        "default": 30,
        "type": "int",
        "applies_to": ["start_server"],
        "description": "How many readiness checks to run before managed startup fails.",
    },
    "startup_wait_seconds": {
        "default": 1.0,
        "type": "float",
        "applies_to": ["start_server"],
        "description": "Sleep interval in seconds between readiness checks during managed startup.",
    },
}


@dataclass(slots=True)
class DucklingDefaults:
    locale: str = "en_US"
    lang: str | None = None
    dims: list[str] | None = None
    latent: bool = False
    tz: str | None = None
    reftime: int | None = None
    request_timeout: float = 10.0
    startup_retries: int = 30
    startup_wait_seconds: float = 1.0


def to_epoch_millis(value: datetime) -> int:
    """Convert a timezone-aware datetime to Unix epoch milliseconds."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware to convert to epoch milliseconds")
    return int(value.timestamp() * 1000)


class DucklingWrapper:
    """Small Python client for Duckling's HTTP API with optional local server management."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        stack_path: str = "stack",
        defaults: DucklingDefaults | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.stack_path = stack_path
        self.defaults = defaults or DucklingDefaults()
        self._session = session or requests.Session()
        self.process: subprocess.Popen[bytes] | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/parse"

    def config(
        self,
        *,
        locale: str | object = _UNSET,
        lang: str | None | object = _UNSET,
        dims: list[str] | None | object = _UNSET,
        latent: bool | object = _UNSET,
        tz: str | None | object = _UNSET,
        reftime: int | None | object = _UNSET,
        request_timeout: float | object = _UNSET,
        startup_retries: int | object = _UNSET,
        startup_wait_seconds: float | object = _UNSET,
    ) -> DucklingWrapper:
        """Update wrapper defaults used by future parse calls and server startup."""
        if locale is not _UNSET:
            self.defaults.locale = str(locale)
        if lang is not _UNSET:
            self.defaults.lang = lang
        if dims is not _UNSET:
            self.defaults.dims = None if dims is None else list(dims)
        if latent is not _UNSET:
            self.defaults.latent = bool(latent)
        if tz is not _UNSET:
            self.defaults.tz = tz
        if reftime is not _UNSET:
            self.defaults.reftime = reftime
        if request_timeout is not _UNSET:
            self.defaults.request_timeout = float(request_timeout)
        if startup_retries is not _UNSET:
            self.defaults.startup_retries = int(startup_retries)
        if startup_wait_seconds is not _UNSET:
            self.defaults.startup_wait_seconds = float(startup_wait_seconds)
        return self

    def get_config(self) -> dict[str, Any]:
        return {
            "locale": self.defaults.locale,
            "lang": self.defaults.lang,
            "dims": None if self.defaults.dims is None else list(self.defaults.dims),
            "latent": self.defaults.latent,
            "tz": self.defaults.tz,
            "reftime": self.defaults.reftime,
            "request_timeout": self.defaults.request_timeout,
            "startup_retries": self.defaults.startup_retries,
            "startup_wait_seconds": self.defaults.startup_wait_seconds,
            "host": self.host,
            "port": self.port,
            "stack_path": self.stack_path,
        }

    @staticmethod
    def get_config_help() -> dict[str, dict[str, Any]]:
        """Return user-facing metadata that explains each constructor and config field."""
        return {name: dict(details) for name, details in _CONFIG_HELP.items()}

    def describe_config(self) -> dict[str, dict[str, Any]]:
        """Return help metadata plus the wrapper's current values."""
        current = self.get_config()
        described: dict[str, dict[str, Any]] = {}
        for name, details in self.get_config_help().items():
            described[name] = {
                **details,
                "current": current.get(name),
            }
        return described

    def start_server(self, duckling_dir: str) -> None:
        """Start a local Duckling server from a Duckling source checkout."""
        if self.process and self.process.poll() is None:
            return

        env = os.environ.copy()
        env["PORT"] = str(self.port)

        self.process = subprocess.Popen(
            [self.stack_path, "exec", "duckling-example-exe"],
            cwd=duckling_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,
        )

        for _ in range(self.defaults.startup_retries):
            if self.is_server_ready():
                return
            time.sleep(self.defaults.startup_wait_seconds)

        self.stop_server()
        raise RuntimeError(f"Duckling server failed to start at {self.url}")

    def stop_server(self) -> None:
        if not self.process:
            return

        if self.process.poll() is None:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                self.process.wait(timeout=5)
        self.process = None

    def is_server_ready(self) -> bool:
        try:
            response = self._session.post(
                self.url,
                data={"text": "ping"},
                timeout=self.defaults.request_timeout,
            )
        except requests.RequestException:
            return False
        return response.status_code == 200

    def parse(
        self,
        text: str,
        *,
        locale: str | None = None,
        lang: str | None = None,
        dims: list[str] | None = None,
        latent: bool | None = None,
        tz: str | None = None,
        reftime: int | None = None,
    ) -> list[dict[str, Any]]:
        """Parse text with Duckling using wrapper defaults plus any per-call overrides."""
        payload = self._build_payload(
            text=text,
            locale=locale,
            lang=lang,
            dims=dims,
            latent=latent,
            tz=tz,
            reftime=reftime,
        )

        response = self._session.post(
            self.url,
            data=payload,
            timeout=self.defaults.request_timeout,
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self.stop_server()
        self._session.close()

    def __enter__(self) -> DucklingWrapper:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _build_payload(
        self,
        *,
        text: str,
        locale: str | None,
        lang: str | None,
        dims: list[str] | None,
        latent: bool | None,
        tz: str | None,
        reftime: int | None,
    ) -> dict[str, str]:
        effective_locale = locale or self.defaults.locale
        effective_lang = lang if lang is not None else self.defaults.lang
        effective_dims = dims if dims is not None else self.defaults.dims
        effective_latent = latent if latent is not None else self.defaults.latent
        effective_tz = tz if tz is not None else self.defaults.tz
        effective_reftime = reftime if reftime is not None else self.defaults.reftime

        payload = {
            "text": text,
            "locale": effective_locale,
            "latent": str(effective_latent).lower(),
        }
        if effective_lang:
            payload["lang"] = effective_lang
        if effective_dims is not None:
            payload["dims"] = json.dumps(effective_dims)
        if effective_tz:
            payload["tz"] = effective_tz
        if effective_reftime is not None:
            payload["reftime"] = str(effective_reftime)
        return payload
