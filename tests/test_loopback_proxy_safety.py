# -*- coding: utf-8 -*-
"""回环地址与代理环境的回归测试（2026-11-15 实测两个真实故障后补）。

本机 NO_PROXY 曾含 `[::1]`：httpx 构造客户端时会把它当 URL 解析，
直接抛 `InvalidURL: Invalid port: ':1]'`，导致 CDP 连接与所有平台 API 请求全挂。
另外 `localhost` 可能解析到 `::1`，Chrome 返回 `ws://[::1]:...` 被 Playwright 拒绝。
"""
import httpx
import pytest

import config
from tools.cdp_browser import CDPBrowserManager
from tools.httpx_util import make_async_client


def test_normalize_ws_url_rewrites_ipv6_loopback():
    assert (
        CDPBrowserManager._normalize_ws_url("ws://[::1]:9222/devtools/browser/abc", 9222)
        == "ws://127.0.0.1:9222/devtools/browser/abc"
    )


def test_normalize_ws_url_rewrites_localhost():
    assert (
        CDPBrowserManager._normalize_ws_url("ws://localhost:9222/devtools/browser/abc", 9222)
        == "ws://127.0.0.1:9222/devtools/browser/abc"
    )


def test_normalize_ws_url_keeps_remote_host():
    url = "ws://example.com:9222/devtools/browser/abc"
    assert CDPBrowserManager._normalize_ws_url(url, 9222) == url


def test_make_async_client_ignores_broken_no_proxy(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_IP_PROXY", False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,[::1]")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:7888")

    client = make_async_client()  # 不应抛 InvalidURL
    try:
        assert client.trust_env is False
    finally:
        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(client.aclose())


def test_make_async_client_disables_trust_env_when_proxy_is_none(monkeypatch):
    """调用方常写 make_async_client(proxy=self.proxy)，proxy 为 None 时也必须直连。"""
    monkeypatch.setattr(config, "ENABLE_IP_PROXY", False)
    monkeypatch.setenv("NO_PROXY", "[::1]")

    client = make_async_client(proxy=None)  # 不应抛 InvalidURL
    try:
        assert client.trust_env is False
    finally:
        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(client.aclose())


def test_make_async_client_keeps_explicit_proxy(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_IP_PROXY", True)
    client = make_async_client(proxy="http://user:pass@127.0.0.1:9000")
    try:
        assert isinstance(client, httpx.AsyncClient)
        assert client.trust_env is True
    finally:
        import asyncio

        asyncio.get_event_loop_policy().new_event_loop().run_until_complete(client.aclose())
