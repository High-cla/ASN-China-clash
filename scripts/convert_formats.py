'''
Author: Vincent Young
Date: 2022-11-17 02:29:30
LastEditors: Vincent Young
LastEditTime: 2022-11-17 03:46:25
FilePath: /ASN-China/scripts/convert_formats.py
Telegram: https://t.me/missuo

Copyright © 2022 by Vincent, All Rights Reserved. 
'''

import sys
from typing import List


INPUT_FILE: str = "IP.China.list"
TXT_OUTPUT: str = "IP.China.txt"
YAML_OUTPUT: str = "IP.China.yaml"


def read_ip_list(filepath: str) -> List[str]:
    """Read raw CIDR lines from IP.China.list, stripping whitespace and skipping empty lines."""
    with open(filepath, "r") as f:
        return [line.strip() for line in f if line.strip()]


def convert_to_txt(cidr_list: List[str]) -> str:
    """Convert CIDR list to IP.China.txt format (IP-CIDR/IP-CIDR6 lines)."""
    lines: List[str] = []
    for cidr in cidr_list:
        if ":" in cidr:
            lines.append(f"IP-CIDR6,{cidr},no-resolve")
        else:
            lines.append(f"IP-CIDR,{cidr},no-resolve")
    return "\n".join(lines) + "\n"


def convert_to_yaml(cidr_list: List[str]) -> str:
    """Convert CIDR list to IP.China.yaml format (payload: with indented IP-CIDR lines)."""
    lines: List[str] = ["payload:"]
    for cidr in cidr_list:
        if ":" in cidr:
            lines.append(f"  - IP-CIDR6,{cidr},no-resolve")
        else:
            lines.append(f"  - IP-CIDR,{cidr},no-resolve")
    return "\n".join(lines) + "\n"


def main() -> None:
    """Read IP.China.list once, produce both IP.China.txt and IP.China.yaml."""
    try:
        cidr_list = read_ip_list(INPUT_FILE)

        if not cidr_list:
            print(f"Warning: {INPUT_FILE} is empty", file=sys.stderr)
            sys.exit(0)

        # Write TXT output
        txt_content = convert_to_txt(cidr_list)
        with open(TXT_OUTPUT, "w") as f:
            f.write(txt_content)

        # Write YAML output
        yaml_content = convert_to_yaml(cidr_list)
        with open(YAML_OUTPUT, "w") as f:
            f.write(yaml_content)

        print(f"Converted {len(cidr_list)} IP ranges to {TXT_OUTPUT} and {YAML_OUTPUT}")
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found - run ChinaIP.py first", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
