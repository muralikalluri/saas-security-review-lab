"""Deliberately insecure for demonstration. Do not deploy.

Offline (respx-mocked, no real network) tests for the token-caching /
auth-error behaviour of isolation_tester.http_client.ApiClient.
"""

import respx
import httpx

from isolation_tester.config import RunConfig, Tenant, UserCred
from isolation_tester.http_client import ApiClient, Actor, AuthError


def _config() -> RunConfig:
    tenant = Tenant(
        id="tenant-a",
        name="Tenant A",
        users={"owner": UserCred(username="alice", password="pw")},
        fixtures={},
    )
    return RunConfig(base_url="http://fake-api.invalid", cache_ttl_seconds=30, tenants=[tenant], enumeration_extra_ids=5)


@respx.mock
def test_token_is_cached_after_first_login():
    config = _config()
    route = respx.post("http://fake-api.invalid/auth/login").mock(
        return_value=httpx.Response(200, json={"access_token": "tok-123"})
    )
    client = ApiClient(config)
    actor = Actor(tenant=config.tenants[0], role="owner", cred=config.tenants[0].users["owner"])

    assert client.token_for(actor) == "tok-123"
    assert client.token_for(actor) == "tok-123"
    assert route.call_count == 1  # second call must hit the cache, not the network


@respx.mock
def test_failed_login_raises_auth_error():
    config = _config()
    respx.post("http://fake-api.invalid/auth/login").mock(return_value=httpx.Response(401, json={"error": "bad creds"}))
    client = ApiClient(config)
    actor = Actor(tenant=config.tenants[0], role="owner", cred=config.tenants[0].users["owner"])

    try:
        client.token_for(actor)
        assert False, "expected AuthError"
    except AuthError:
        pass


@respx.mock
def test_authenticated_call_sends_bearer_header():
    config = _config()
    respx.post("http://fake-api.invalid/auth/login").mock(return_value=httpx.Response(200, json={"access_token": "tok-abc"}))
    call_route = respx.get("http://fake-api.invalid/invoices/1").mock(return_value=httpx.Response(200, json={"id": 1}))

    client = ApiClient(config)
    actor = Actor(tenant=config.tenants[0], role="owner", cred=config.tenants[0].users["owner"])
    response = client.call("get", "/invoices/1", actor)

    assert response.status_code == 200
    assert call_route.calls.last.request.headers["Authorization"] == "Bearer tok-abc"
