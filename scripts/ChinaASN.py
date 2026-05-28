'''
Author: Vincent Young
Date: 2022-11-17 02:29:30
LastEditors: Vincent Young
LastEditTime: 2022-11-17 03:46:25
FilePath: /ASN-China/scripts/ChinaASN.py
Telegram: https://t.me/missuo

Copyright © 2022 by Vincent, All Rights Reserved. 
'''
import re
import time
from typing import List, Tuple

import requests

URL: str = "https://bgp.he.net/country/CN"
HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
OUTPUT_FILE: str = "ASN.China.list"
TIMEOUT: int = 30


def init_file() -> None:
    """Initialize the output file with header comments."""
    local_time: str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(OUTPUT_FILE, "w", encoding="utf-8") as asn_file:
        asn_file.write("# ASN Information in China. (https://github.com/missuo/ASN-China) \n")
        asn_file.write(f"# Last Updated: UTC {local_time}\n")
        asn_file.write("# Made by Vincent, All rights reserved. \n")
        asn_file.write("payload: \n")


def fetch_asn_data() -> List[Tuple[str, str]]:
    """Fetch ASN data from bgp.he.net and parse it.

    Returns:
        A list of (asn_number, asn_name) tuples.
    """
    try:
        r = requests.get(URL, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching data from {URL}: {e}")
        return []

    html: str = r.text
    asns: List[Tuple[str, str]] = []

    # Parse HTML table rows for ASN data.
    # Pattern matches: <td>...AS<number>...</td> followed by <td><name></td>
    # Handles both <a href="/AS12345">AS12345</a> and plain AS12345.
    pattern: str = r'<td[^>]*>.*?AS(\d+).*?</td>\s*<td[^>]*>([^<]*)</td>'
    matches: List[Tuple[str, str]] = re.findall(pattern, html, re.DOTALL)

    for asn_number, asn_name in matches:
        name: str = asn_name.strip()
        if name:
            asns.append((asn_number, name))

    return asns


def save_latest_asn() -> None:
    """Fetch and save the latest ASN data to the output file."""
    asn_data: List[Tuple[str, str]] = fetch_asn_data()

    if not asn_data:
        print("No ASN data retrieved. Output file will not be updated.")
        return

    init_file()
    with open(OUTPUT_FILE, "a", encoding="utf-8") as asn_file:
        for asn_number, asn_name in asn_data:
            asn_info: str = f"- IP-ASN,{asn_number}#{asn_name}"
            asn_file.write(asn_info + "\n")

    print(f"Successfully wrote {len(asn_data)} ASN entries to {OUTPUT_FILE}")


if __name__ == "__main__":
    save_latest_asn()
