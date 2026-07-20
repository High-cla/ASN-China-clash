"""Fetch China IP prefixes, union sources, collapse, no intermediate list files."""
from __future__ import annotations

import ipaddress
import os
import sys
from pathlib import Path
from typing import Iterable

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

DEFAULT_IP_SOURCES: list[str] = [
    "https://raw.githubusercontent.com/cbuijs/ipasn/master/country-asia-china.list",
    "https://raw.githubusercontent.com/cbuijs/ipasn/master/country-asia-china4.list",
    "https://raw.githubusercontent.com/cbuijs/ipasn/master/country-asia-china6.list",
]

REQUEST_TIMEOUT: int = int(os.environ.get("REQUEST_TIMEOUT", "30"))
USER_AGENT: str = os.environ.get(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)


def ip_sources() -> list[str]:
    raw = os.environ.get("IP_SOURCES", "").strip()
    if not raw:
        return list(DEFAULT_IP_SOURCES)
    return [u.strip() for u in raw.split(",") if u.strip()]


def parse_cidr_lines(lines: Iterable[str]) -> list[ipaddress._BaseNetwork]:
    nets: list[ipaddress._BaseNetwork] = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        try:
            nets.append(ipaddress.ip_network(s, strict=False))
        except ValueError:
            continue
    return nets


def collapse_cidrs(nets: list[ipaddress._BaseNetwork]) -> list[str]:
    if not nets:
        return []
    collapsed = ipaddress.collapse_addresses(nets)
    return [str(n) for n in collapsed]


def fetch_url(url: str) -> str | None:
    try:
        r = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"IP source failed {url}: {e}", file=sys.stderr)
        return None


def fetch_and_collapse() -> list[str]:
    """Union all sources, parse, collapse. Empty list if all sources fail."""
    raw_lines: list[str] = []
    ok = 0
    for url in ip_sources():
        body = fetch_url(url)
        if body is None:
            continue
        ok += 1
        raw_lines.extend(body.splitlines())
    if ok == 0:
        print("All IP sources failed", file=sys.stderr)
        return []
    before = parse_cidr_lines(raw_lines)
    after = collapse_cidrs(before)
    print(f"IP: sources_ok={ok} before_collapse={len(before)} after_collapse={len(after)}")
    return after


def main() -> None:
    cidrs = fetch_and_collapse()
    if not cidrs:
        sys.exit(1)
    print(f"fetch_and_collapse returned {len(cidrs)} CIDRs (no list file written)")


if __name__ == "__main__":
    main()
