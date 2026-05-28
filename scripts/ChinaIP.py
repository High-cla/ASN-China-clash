"""
Author: Vincent Young
Date: 2022-11-17 02:14:24
LastEditors: Vincent Young
LastEditTime: 2022-11-17 03:19:20
FilePath: /ASN-China/syncIP.py
Telegram: https://t.me/missuo

Copyright © 2022 by Vincent, All Rights Reserved.

Download China IP lists from cbuijs/ipasn and save to files.
"""

import sys
from typing import NoReturn

import requests

# URL constants
ALL_CHINA_URL: str = "https://raw.githubusercontent.com/cbuijs/ipasn/master/country-asia-china.list"
V4_CHINA_URL: str = "https://raw.githubusercontent.com/cbuijs/ipasn/master/country-asia-china4.list"
V6_CHINA_URL: str = "https://raw.githubusercontent.com/cbuijs/ipasn/master/country-asia-china6.list"

# Output file names
ALL_CHINA_FILE: str = "IP.China.list"
V4_CHINA_FILE: str = "IPv4.China.list"
V6_CHINA_FILE: str = "IPv6.China.list"

REQUEST_TIMEOUT: int = 30


def download_file(url: str, output_path: str) -> None:
    """Download a file from the given URL and save it to output_path."""
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(r.content)
        print(f"Downloaded: {output_path}")
    except requests.RequestException as e:
        print(f"Error downloading {url}: {e}", file=sys.stderr)


def main() -> None:
    """Download all China IP lists."""
    download_file(ALL_CHINA_URL, ALL_CHINA_FILE)
    download_file(V4_CHINA_URL, V4_CHINA_FILE)
    download_file(V6_CHINA_URL, V6_CHINA_FILE)


if __name__ == "__main__":
    main()
