"""Fetch China ASN list; regex primary, optional lxml fallback; atomic write."""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from atomic_write import atomic_write  # noqa: E402

DEFAULT_ASN_URLS = ["https://bgp.he.net/country/CN"]
OUTPUT_FILE = "ASN.China.list"
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30"))
USER_AGENT = os.environ.get(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)
ROW_RE = re.compile(
    r"<td[^>]*>.*?AS(\d+).*?</td>\s*<td[^>]*>([^<]*)</td>",
    re.DOTALL,
)


def asn_urls() -> list[str]:
    raw = os.environ.get("ASN_URLS", "").strip()
    if not raw:
        return list(DEFAULT_ASN_URLS)
    return [u.strip() for u in raw.split(",") if u.strip()]


def parse_regex(html: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for num, name in ROW_RE.findall(html):
        n = name.strip()
        if n:
            out.append((int(num), n))
    return out


def parse_lxml(html: str) -> list[tuple[int, str]]:
    try:
        from lxml import html as lhtml  # type: ignore
    except ImportError:
        return []
    doc = lhtml.fromstring(html)
    out: list[tuple[int, str]] = []
    for tr in doc.xpath("//table//tr"):
        tds = tr.xpath("./td")
        if len(tds) < 2:
            continue
        text0 = "".join(tds[0].itertext())
        m = re.search(r"AS(\d+)", text0)
        if not m:
            continue
        name = "".join(tds[1].itertext()).strip()
        if name:
            out.append((int(m.group(1)), name))
    return out


def dedupe_sort(rows: list[tuple[int, str]]) -> list[tuple[int, str]]:
    seen: dict[int, str] = {}
    for num, name in rows:
        if num not in seen:
            seen[num] = name
        elif name and not seen[num]:
            seen[num] = name
    return sorted(seen.items(), key=lambda x: x[0])


def fetch_html(url: str) -> str | None:
    try:
        r = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"ASN URL failed {url}: {e}", file=sys.stderr)
        return None


def collect_asns() -> list[tuple[int, str]]:
    for url in asn_urls():
        html = fetch_html(url)
        if not html:
            continue
        rows = parse_regex(html)
        if not rows:
            rows = parse_lxml(html)
            if rows:
                print(f"ASN: used lxml fallback for {url}")
        if rows:
            return dedupe_sort(rows)
        print(f"ASN: no rows parsed from {url}", file=sys.stderr)
    return []


def render(asns: list[tuple[int, str]]) -> str:
    local_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    lines = [
        "# ASN Information in China. (https://github.com/High-cla/ASN-China-clash)",
        f"# Last Updated: UTC {local_time}",
        "# Made by Vincent / High-cla fork. All rights reserved.",
        "payload:",
    ]
    for num, _name in asns:
        lines.append(f"- IP-ASN,{num}")
    return "\n".join(lines) + "\n"


def main() -> None:
    asns = collect_asns()
    if not asns:
        print("No ASN data; refusing to write", file=sys.stderr)
        sys.exit(1)
    atomic_write(OUTPUT_FILE, render(asns))
    print(f"Wrote {len(asns)} ASN entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
