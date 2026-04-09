from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import requests

from qwackling import DucklingWrapper, to_epoch_millis


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")

    def json(self):
        return self._payload


def test_parse_uses_wrapper_config_defaults():
    wrapper = DucklingWrapper().config(
        locale="fr_FR",
        lang="FR",
        dims=["time"],
        latent=True,
        tz="Asia/Kolkata",
        reftime=1775622600000,
        request_timeout=7.5,
    )
    wrapper._session.post = MagicMock(return_value=DummyResponse([{"body": "ok"}]))

    results = wrapper.parse("demain a 20h")

    assert results == [{"body": "ok"}]
    wrapper._session.post.assert_called_once_with(
        wrapper.url,
        data={
            "text": "demain a 20h",
            "locale": "fr_FR",
            "lang": "FR",
            "dims": '["time"]',
            "latent": "true",
            "tz": "Asia/Kolkata",
            "reftime": "1775622600000",
        },
        timeout=7.5,
    )


def test_parse_allows_per_call_overrides():
    wrapper = DucklingWrapper().config(locale="en_US", tz="UTC", reftime=111)
    wrapper._session.post = MagicMock(return_value=DummyResponse([{"body": "ok"}]))

    wrapper.parse(
        "tomorrow at 8pm",
        locale="en_GB",
        dims=["time", "numeral"],
        latent=False,
        tz="Asia/Kolkata",
        reftime=1775622600000,
    )

    call = wrapper._session.post.call_args
    assert call.kwargs["data"]["locale"] == "en_GB"
    assert call.kwargs["data"]["dims"] == '["time", "numeral"]'
    assert call.kwargs["data"]["tz"] == "Asia/Kolkata"
    assert call.kwargs["data"]["reftime"] == "1775622600000"


def test_config_can_clear_optional_defaults():
    wrapper = DucklingWrapper().config(tz="UTC", reftime=123, dims=["time"])
    wrapper.config(tz=None, reftime=None, dims=None)

    current = wrapper.get_config()

    assert current["tz"] is None
    assert current["reftime"] is None
    assert current["dims"] is None


def test_build_payload_omits_unset_optional_fields():
    wrapper = DucklingWrapper()

    payload = wrapper._build_payload(
        text="tomorrow",
        locale=None,
        lang=None,
        dims=None,
        latent=None,
        tz=None,
        reftime=None,
    )

    assert payload == {
        "text": "tomorrow",
        "locale": "en_US",
        "latent": "false",
    }


def test_config_help_exposes_meaningful_metadata():
    help_text = DucklingWrapper.get_config_help()

    assert help_text["tz"]["type"] == "str | None"
    assert "timezone" in help_text["tz"]["description"].lower()
    assert help_text["host"]["default"] == "127.0.0.1"


def test_describe_config_includes_current_values():
    wrapper = DucklingWrapper(host="duckling", port=9000).config(tz="UTC", dims=["time"])

    described = wrapper.describe_config()

    assert described["host"]["current"] == "duckling"
    assert described["port"]["current"] == 9000
    assert described["tz"]["current"] == "UTC"
    assert described["dims"]["current"] == ["time"]


def test_start_server_sets_port_and_waits_for_healthcheck():
    wrapper = DucklingWrapper(port=8123).config(
        request_timeout=2.0,
        startup_retries=3,
        startup_wait_seconds=0.01,
    )
    process = MagicMock()
    process.poll.return_value = None
    process.pid = 4242

    with patch("qwackling.client.subprocess.Popen", return_value=process) as popen:
        with patch.object(wrapper, "is_server_ready", side_effect=[False, True]) as ready:
            with patch("qwackling.client.time.sleep") as sleep:
                wrapper.start_server("./duckling")

    popen.assert_called_once()
    assert popen.call_args.kwargs["env"]["PORT"] == "8123"
    assert ready.call_count == 2
    sleep.assert_called_once_with(0.01)


def test_start_server_raises_if_healthcheck_never_passes():
    wrapper = DucklingWrapper(port=8123).config(
        startup_retries=2,
        startup_wait_seconds=0.01,
    )
    process = MagicMock()
    process.poll.return_value = None
    process.pid = 4242

    with patch("qwackling.client.subprocess.Popen", return_value=process):
        with patch.object(wrapper, "is_server_ready", return_value=False):
            with patch.object(wrapper, "stop_server") as stop_server:
                with patch("qwackling.client.time.sleep"):
                    with pytest.raises(RuntimeError, match="failed to start"):
                        wrapper.start_server("./duckling")

    stop_server.assert_called_once()


def test_to_epoch_millis_requires_timezone_aware_datetime():
    aware = datetime.fromisoformat("2026-04-08T10:00:00+05:30")
    assert to_epoch_millis(aware) == 1775622600000

    naive = datetime(2026, 4, 8, 10, 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        to_epoch_millis(naive)
