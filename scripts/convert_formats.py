"""Convert collapsed China IP CIDRs to Clash txt/yaml rule files."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atomic_write import atomic_write  # noqa: E402
from ChinaIP import fetch_and_collapse  # noqa: E402

TXT_OUTPUT = "IP.China.txt"
YAML_OUTPUT = "IP.China.yaml"
YAML_V4 = "IP.China.ipv4.yaml"
YAML_V6 = "IP.China.ipv6.yaml"


def rule_for(cidr: str) -> str:
    if ":" in cidr:
        return f"IP-CIDR6,{cidr},no-resolve"
    return f"IP-CIDR,{cidr},no-resolve"


def to_txt(cidrs: list[str]) -> str:
    return "\n".join(rule_for(c) for c in cidrs) + "\n"


def to_yaml(cidrs: list[str]) -> str:
    lines = ["payload:"]
    for c in cidrs:
        lines.append(f"  - {rule_for(c)}")
    return "\n".join(lines) + "\n"


def split_v4_v6(cidrs: list[str]) -> tuple[list[str], list[str]]:
    v4: list[str] = []
    v6: list[str] = []
    for c in cidrs:
        if ":" in c:
            v6.append(c)
        else:
            v4.append(c)
    return v4, v6


def main() -> None:
    cidrs = fetch_and_collapse()
    if not cidrs:
        print("No CIDRs; refusing to write outputs", file=sys.stderr)
        sys.exit(1)
    v4, v6 = split_v4_v6(cidrs)
    if not v4 or not v6:
        print("Missing v4 or v6 after split; refusing partial write", file=sys.stderr)
        sys.exit(1)
    atomic_write(TXT_OUTPUT, to_txt(cidrs))
    atomic_write(YAML_OUTPUT, to_yaml(cidrs))
    atomic_write(YAML_V4, to_yaml(v4))
    atomic_write(YAML_V6, to_yaml(v6))
    print(
        f"Wrote {TXT_OUTPUT}, {YAML_OUTPUT}, {YAML_V4}, {YAML_V6} "
        f"(total={len(cidrs)} v4={len(v4)} v6={len(v6)})"
    )


if __name__ == "__main__":
    main()
