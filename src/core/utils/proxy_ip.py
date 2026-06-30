"""Resolve real client IP behind a trusted reverse proxy / load balancer.

Behind Cloud Run / a load balancer / nginx the `request.client.host` is the LB
IP, not the user's IP. Rate limiting on the LB IP shares the bucket across every
client → useless. This helper resolves the real client from `X-Forwarded-For`,
either by walking right-to-left skipping trusted-CIDR hops, or — when
`TRUSTED_PROXY_HOP_COUNT > 0` — by reading a fixed offset from the right (the hop
the LB guarantees), which is spoof-proof against a client-supplied XFF prefix.

If the request did not come through a proxy, the raw socket IP is returned (so
direct-to-pod local dev still works).
"""

from __future__ import annotations

import ipaddress
from functools import lru_cache
from typing import TYPE_CHECKING

from src.core.config import settings

if TYPE_CHECKING:
    from fastapi import Request


@lru_cache(maxsize=1)
def _trusted_networks() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    raw = settings.TRUSTED_PROXIES or ""
    out: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            out.append(ipaddress.ip_network(token, strict=False))
        except ValueError:
            # Skip invalid entries silently — better than crashing the request path.
            continue
    return tuple(out)


def _is_trusted(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(addr in net for net in _trusted_networks())


def get_client_ip(request: Request) -> str:
    """Return the best-guess client IP for the current request.

    Fixed-hop mode (`TRUSTED_PROXY_HOP_COUNT > 0`) reads the client at a fixed
    offset from the right of `X-Forwarded-For`, ignoring a client-supplied
    prefix. Otherwise walks right-to-left and returns the first hop NOT inside
    `TRUSTED_PROXIES`. Falls back to the raw socket peer when XFF is absent.
    """
    raw_peer = request.client.host if request.client else "0.0.0.0"
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return raw_peer

    # XFF is "client, proxy1, proxy2"; reverse to walk from edge inward.
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]

    hop_count = settings.TRUSTED_PROXY_HOP_COUNT
    if hop_count > 0:
        idx = hop_count + 1
        return hops[-idx] if len(hops) >= idx else raw_peer

    for hop in reversed(hops):
        if not _is_trusted(hop):
            return hop
    # All hops are trusted (rare); first hop is the originator.
    return hops[0] if hops else raw_peer
