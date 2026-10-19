import pytest
from fastapi import HTTPException
from starlette.requests import Request

from epidemiological_agent.api import rate_limit
from epidemiological_agent.api.rate_limit import RateLimiter, client_ip


def _request(forwarded_for: str | None = None, host: str = "127.0.0.1") -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": headers,
            "client": (host, 12345),
        }
    )


def test_client_ip_uses_last_forwarded_for_entry():
    assert client_ip(_request("1.1.1.1, 203.0.113.7")) == "203.0.113.7"


def test_client_ip_falls_back_to_tcp_peer():
    assert client_ip(_request(host="198.51.100.2")) == "198.51.100.2"


def test_limiter_blocks_after_max_requests_with_retry_after():
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    request = _request("203.0.113.7")

    limiter(request)
    limiter(request)

    with pytest.raises(HTTPException) as error:
        limiter(request)

    assert error.value.status_code == 429
    assert 0 < int(error.value.headers["Retry-After"]) <= 60


def test_limiter_counts_each_ip_separately():
    limiter = RateLimiter(max_requests=1, window_seconds=60)

    limiter(_request("203.0.113.7"))
    limiter(_request("203.0.113.8"))


def test_limiter_frees_slot_after_window(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: clock[0])

    limiter = RateLimiter(max_requests=1, window_seconds=60)
    request = _request("203.0.113.7")

    limiter(request)
    clock[0] += 60
    limiter(request)
