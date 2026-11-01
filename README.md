# ASN-China-clash

High-cla fork of [missuo/ASN-China](https://github.com/missuo/ASN-China): daily China ASN + IP lists with **Clash/Mihomo** rule-provider outputs, CIDR collapse, and CI validation gates.

## Features

- Daily GitHub Actions update (UTC 16:00 schedule + manual dispatch)
- ASN from bgp.he.net (regex with lxml parser fallback, multi-URL via `ASN_URLS`)
- IP from cbuijs/ipasn (multi-source **union**, `ipaddress` collapse; `IP_SOURCES` overridable)
- Outputs: `ASN.China.list`, `IP.China.txt`, `IP.China.yaml`, `IP.China.ipv4.yaml`, `IP.China.ipv6.yaml`
- Empty/partial results are **not** committed (`validate_outputs.py`)

## Clash / Mihomo

Raw base: `https://raw.githubusercontent.com/High-cla/ASN-China-clash/main/`

```yaml
rule-providers:
  china-ip:
    type: http
    behavior: classical
    url: "https://raw.githubusercontent.com/High-cla/ASN-China-clash/main/IP.China.yaml"
    path: ./ruleset/china-ip.yaml
    interval: 86400
  china-ip-v4:
    type: http
    behavior: classical
    url: "https://raw.githubusercontent.com/High-cla/ASN-China-clash/main/IP.China.ipv4.yaml"
    path: ./ruleset/china-ip-v4.yaml
    interval: 86400
  china-ip-v6:
    type: http
    behavior: classical
    url: "https://raw.githubusercontent.com/High-cla/ASN-China-clash/main/IP.China.ipv6.yaml"
    path: ./ruleset/china-ip-v6.yaml
    interval: 86400
  china-asn:
    type: http
    behavior: classical
    url: "https://raw.githubusercontent.com/High-cla/ASN-China-clash/main/ASN.China.list"
    path: ./ruleset/china-asn.yaml
    interval: 86400

rules:
  - RULE-SET,china-ip,DIRECT
  # - RULE-SET,china-asn,DIRECT   # if your core supports IP-ASN in classical providers
```

Also available: `IP.China.txt` (line format `IP-CIDR` / `IP-CIDR6` + `,no-resolve`) for clients that ingest text rule lists.

## vs missuo/ASN-China

| | missuo | this fork |
|--|--------|-----------|
| Clash yaml/txt | no | yes (+ v4/v6 split) |
| CIDR collapse | no | yes |
| Intermediate `IP.China.list` | yes | not written |
| CI gate | basic | `validate_outputs` min counts |

## Data sources

- ASN: [bgp.he.net/country/CN](https://bgp.he.net/country/CN) (`ASN_URLS` comma-separated)
- IP: [cbuijs/ipasn](https://github.com/cbuijs/ipasn) (`IP_SOURCES` comma-separated)

## Local run

Python 3.10 or newer:

```bash
pip install -r requirements.txt
python scripts/ChinaASN.py
python scripts/convert_formats.py
python scripts/validate_outputs.py
```

Environment variables: `REQUEST_TIMEOUT`, `USER_AGENT`, `MIN_ASN_COUNT` (default 100), `MIN_CIDR_COUNT` (default 1000).

## Upstream synchronization policy

This repository tracks [missuo/ASN-China](https://github.com/missuo/ASN-China), but intentionally keeps its China-focused Clash/Mihomo generation pipeline.

- Keep `scripts/ChinaASN.py` and `scripts/ChinaIP.py` as the maintained fetch/normalization layer; do not replace them wholesale with the upstream legacy scripts.
- Generate `ASN.China.list` and all Clash/Mihomo text/YAML artifacts through this fork's scripts. Do not manually patch generated lists or copy upstream list files over them.
- Keep `scripts/convert_formats.py`, `scripts/atomic_write.py`, `scripts/validate_outputs.py`, tests, and the validation workflow as fork-specific functionality.
- Upstream-only US ASN artifacts (`ASN.US.list` and `scripts/ASN_US.py`) are intentionally out of scope for this China-only repository.

## Network reliability and dependencies

- Shared HTTP GET requests use bounded retries for connection/read failures and transient HTTP statuses (429, 500, 502, 503, 504), with exponential backoff and `Retry-After` support.
- Direct Python dependencies are pinned in `requirements.txt`; Dependabot checks Python packages and GitHub Actions weekly.
- The optional ASN-derived IP-prefix dataset remains separate from the geographically sourced China IP rules to avoid changing the meaning of the existing rule provider.

## License

MIT (see [LICENSE](./LICENSE)). Original work (c) Vincent Young / missuo; this fork maintains Clash-oriented tooling.
