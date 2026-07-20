"""Read-only gates for ASN/IP pipeline outputs."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REQUIRED = [
    "ASN.China.list",
    "IP.China.txt",
    "IP.China.yaml",
    "IP.China.ipv4.yaml",
    "IP.China.ipv6.yaml",
]

MIN_ASN = int(os.environ.get("MIN_ASN_COUNT", "100"))
MIN_CIDR = int(os.environ.get("MIN_CIDR_COUNT", "1000"))

ASN_LINE = re.compile(r"^- IP-ASN,\d+\s*$", re.M)
TXT_LINE = re.compile(r"^IP-CIDR6?,[0-9a-fA-F:./]+,no-resolve\s*$")
YAML_ITEM = re.compile(r"^  - (IP-ASN,\d+|IP-CIDR6?,[0-9a-fA-F:./]+,no-resolve)\s*$")


def fail(msg: str) -> None:
    print(f"validate FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def count_asn(text: str) -> int:
    return len(ASN_LINE.findall(text))


def count_txt_cidrs(text: str) -> int:
    return sum(1 for line in text.splitlines() if TXT_LINE.match(line))


def yaml_payload_items(text: str) -> list[str]:
    if "payload:" not in text:
        fail("yaml missing payload:")
    items: list[str] = []
    for line in text.splitlines():
        m = YAML_ITEM.match(line)
        if m:
            items.append(m.group(1))
    return items


def main() -> None:
    root = Path.cwd()
    for name in REQUIRED:
        p = root / name
        if not p.is_file():
            fail(f"missing {name}")
        if p.stat().st_size == 0:
            fail(f"empty {name}")

    asn_text = (root / "ASN.China.list").read_text(encoding="utf-8", errors="replace")
    asn_n = count_asn(asn_text)
    if asn_n < MIN_ASN:
        fail(f"ASN count {asn_n} < MIN_ASN_COUNT={MIN_ASN}")

    txt = (root / "IP.China.txt").read_text(encoding="utf-8", errors="replace")
    cidr_n = count_txt_cidrs(txt)
    if cidr_n < MIN_CIDR:
        fail(f"CIDR count {cidr_n} < MIN_CIDR_COUNT={MIN_CIDR}")

    for yname in ("IP.China.yaml", "IP.China.ipv4.yaml", "IP.China.ipv6.yaml"):
        items = yaml_payload_items((root / yname).read_text(encoding="utf-8", errors="replace"))
        if not items:
            fail(f"{yname} has no payload items")

    v4_items = yaml_payload_items((root / "IP.China.ipv4.yaml").read_text(encoding="utf-8", errors="replace"))
    if any(i.startswith("IP-CIDR6,") for i in v4_items):
        fail("IP.China.ipv4.yaml contains IP-CIDR6")
    if not all(i.startswith("IP-CIDR,") for i in v4_items):
        fail("IP.China.ipv4.yaml has non-IPv4 items")

    v6_items = yaml_payload_items((root / "IP.China.ipv6.yaml").read_text(encoding="utf-8", errors="replace"))
    if any(i.startswith("IP-CIDR,") and not i.startswith("IP-CIDR6,") for i in v6_items):
        fail("IP.China.ipv6.yaml contains IPv4 IP-CIDR")
    if not all(i.startswith("IP-CIDR6,") for i in v6_items):
        fail("IP.China.ipv6.yaml has non-IPv6 items")

    all_items = yaml_payload_items((root / "IP.China.yaml").read_text(encoding="utf-8", errors="replace"))
    print(
        f"validate OK: asn={asn_n} cidr_txt={cidr_n} "
        f"yaml_all={len(all_items)} v4={len(v4_items)} v6={len(v6_items)}"
    )


if __name__ == "__main__":
    main()
