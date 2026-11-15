# -*- coding: utf-8 -*-
import httpx
import config


def make_async_client(**kwargs) -> httpx.AsyncClient:
    """创建统一配置的 httpx.AsyncClient。

    从配置文件读取 DISABLE_SSL_VERIFY（默认 False，即开启 SSL 验证）。
    仅在使用企业代理、Burp、mitmproxy 等中间人代理时才需将其设为 True。
    """
    kwargs.setdefault("verify", not getattr(config, "DISABLE_SSL_VERIFY", False))
    # 默认未开启代理时，禁止 httpx 读取系统/环境代理，保证爬虫流量直连防止漏出机场配额。
    # 注意：调用方常写 make_async_client(proxy=self.proxy)，self.proxy 为 None 时
    # key 已存在，因此必须按「值为空」判断；否则 httpx 仍会读环境变量，遇到
    # 形如 [::1] 的 NO_PROXY 条目会在构造客户端的瞬间抛 InvalidURL: Invalid port: ':1]'。
    if not getattr(config, "ENABLE_IP_PROXY", False):
        explicit_proxy = kwargs.get("proxy") or kwargs.get("proxies")
        if not explicit_proxy:
            kwargs.setdefault("trust_env", False)
    return httpx.AsyncClient(**kwargs)
