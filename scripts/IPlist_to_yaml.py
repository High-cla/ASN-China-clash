'''
Author: Vincent Young
Date: 2022-11-17 02:29:30
LastEditors: Vincent Young
LastEditTime: 2022-11-17 03:46:25
FilePath: /ASN-China/scripts/IPlist_to_yaml.py
Telegram: https://t.me/missuo

Copyright © 2022 by Vincent, All Rights Reserved. 
'''

import sys
from typing import List


INPUT_FILE: str = "IP.China.txt"
OUTPUT_FILE: str = "IP.China.yaml"


def read_ip_txt(filepath: str) -> List[str]:
    """Read IP-CIDR lines from IP.China.txt, stripping whitespace."""
    with open(filepath, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def convert_to_yaml(lines: List[str]) -> str:
    """Convert IP-CIDR lines to YAML format with 'payload:' header."""
    output: str = 'payload:\n'
    for line in lines:
        output += f"  - {line}\n"
    return output


def main() -> None:
    """Main entry point: read IP.China.txt, write IP.China.yaml."""
    try:
        ip_lines = read_ip_txt(INPUT_FILE)
        yaml_content = convert_to_yaml(ip_lines)
        with open(OUTPUT_FILE, 'w') as f:
            f.write(yaml_content)
        print(f"Converted {len(ip_lines)} IP ranges to {OUTPUT_FILE}")
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
