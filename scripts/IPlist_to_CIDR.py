'''
Author: Vincent Young
Date: 2022-11-17 02:29:30
LastEditors: Vincent Young
LastEditTime: 2022-11-17 03:46:25
FilePath: /ASN-China/scripts/IPlist_to_CIDR.py
Telegram: https://t.me/missuo

Copyright © 2022 by Vincent, All Rights Reserved. 

NOTE: This script is superseded by convert_formats.py which handles
both CIDR and YAML conversion in a single pass.
'''

import sys
from typing import List


INPUT_FILE: str = "IP.China.list"
OUTPUT_FILE: str = "IP.China.txt"


def read_ip_list(filepath: str) -> List[str]:
    """Read raw CIDR lines from file, stripping whitespace and skipping empty lines."""
    with open(filepath, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def convert_to_txt(cidr_list: List[str]) -> str:
    """Convert CIDR list to IP-CIDR / IP-CIDR6 lines with no-resolve flag."""
    lines: List[str] = []
    for cidr in cidr_list:
        if ":" in cidr:
            lines.append(f"IP-CIDR6,{cidr},no-resolve")
        else:
            lines.append(f"IP-CIDR,{cidr},no-resolve")
    return "\n".join(lines) + "\n"


def main() -> None:
    """Read IP.China.list, write IP.China.txt with IP-CIDR format."""
    try:
        cidr_list = read_ip_list(INPUT_FILE)
        if not cidr_list:
            print(f"Warning: {INPUT_FILE} is empty", file=sys.stderr)
            sys.exit(0)
        content = convert_to_txt(cidr_list)
        with open(OUTPUT_FILE, 'w') as f:
            f.write(content)
        print(f"Converted {len(cidr_list)} IP ranges to {OUTPUT_FILE}")
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found - run ChinaIP.py first", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
