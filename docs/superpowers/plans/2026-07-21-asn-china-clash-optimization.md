# ASN-China-clash 完整档优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 High-cla/ASN-China-clash 上完成完整档 C：ASN/IP 抓取加固、CIDR 聚合、Clash 分卷 yaml、validate 门禁、死代码清理、README Clash 文档；全程云端改仓库。

**Architecture:** 保持 `scripts/` 布局。ChinaASN 多 URL + regex（可选 lxml）→ 原子写 `ASN.China.list`。ChinaIP 暴露 `fetch_and_collapse() -> list[str]`（多源并集 + `ipaddress.collapse_addresses`，不落盘中间 list）。convert_formats 直调 ChinaIP，一次写 txt + 全量/v4/v6 yaml。validate_outputs 只读门禁。CI 同 job 串行：ASN → convert → validate → auto-commit。

**Tech Stack:** Python 3.12, requests==2.32.3, stdlib `ipaddress`/`re`/`os`, 可选 lxml（ASN 回退）, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-07-21-asn-china-clash-optimization-design.md`  
**Repo:** https://github.com/High-cla/ASN-China-clash  
**约束:** 云端 PR 改仓库；分支名 ≤3 词连字符（如 `opt-asn-clash`）；commit `type(scope): summary`

---

## File map

| 路径 | 动作 | 职责 |
|------|------|------|
| `scripts/atomic_write.py` | Create | `atomic_write(path, content)`：tmp + replace，空内容拒绝 |
| `scripts/ChinaASN.py` | Rewrite | 多 URL、regex+可选 lxml、排序去重、一次拼串原子写、失败 exit 1 |
| `scripts/ChinaIP.py` | Rewrite | `fetch_and_collapse()`、多源并集、collapse、CLI 不写 list |
| `scripts/convert_formats.py` | Rewrite | 直调 ChinaIP；写 4 个 IP 产物；空 exit 1 |
| `scripts/validate_outputs.py` | Create | 只读校验必需文件/下限/payload/v4·v6 隔离 |
| `scripts/IPlist_to_CIDR.py` | Delete | 死代码 |
| `scripts/IPlist_to_yaml.py` | Delete | 死代码 |
| `IP.China.list` | Delete | 停更中间产物 |
| `IPv4.China.list` | Delete | 废弃 |
| `IPv6.China.list` | Delete | 废弃 |
| `.github/workflows/ci.yml` | Modify | 串行 + validate；CI 装 lxml |
| `requirements.txt` | Keep | `requests==2.32.3` only |
| `README.md` | Rewrite | High-cla raw + Clash/Mihomo 示例 + 产物表 |
| `tests/test_collapse.py` | Create (optional) | collapse / parse 单元测 |

**导入约定（写死）:** 仓库根运行 `python scripts/<name>.py`。各脚本入口前：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
```

**默认 IP 源（写死）:**

```text
https://raw.githubusercontent.com/cbuijs/ipasn/master/country-asia-china.list
https://raw.githubusercontent.com/cbuijs/ipasn/master/country-asia-china4.list
https://raw.githubusercontent.com/cbuijs/ipasn/master/country-asia-china6.list
```

**默认 ASN URL:** `https://bgp.he.net/country/CN`

---

### Task 1: atomic_write 工具

**Files:**
- Create: `scripts/atomic_write.py`

- [ ] **Step 1: 写 `scripts/atomic_write.py`**

```python
"""Atomic file replace helpers."""
from __future__ import annotations

import os
from pathlib import Path


def atomic_write(path: str | Path, content: str, encoding: str = "utf-8") -> None:
    """Write content via temp file + os.replace. Reject empty content."""
    if not content:
        raise ValueError(f"refusing empty write: {path}")
    target = Path(path)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    if tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"refusing empty file: {path}")
    os.replace(tmp, target)
```

- [ ] **Step 2: 冒烟**

```bash
python -c "
import sys; sys.path.insert(0,'scripts')
from atomic_write import atomic_write
from pathlib import Path
p=Path('_atomic_smoke.txt')
atomic_write(p,'hello\n')
assert p.read_text()=='hello\n'
p.unlink()
print('ok')
"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add scripts/atomic_write.py
git commit -m "feat(scripts): add atomic_write helper"
```

---

### Task 2: validate_outputs.py

**Files:**
- Create: `scripts/validate_outputs.py`

- [ ] **Step 1: 实现校验脚本**

```python
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
```

- [ ] **Step 2: 对当前仓库产物试跑（旧产物缺 ipv4/v6 yaml 时期望 FAIL）**

```bash
python scripts/validate_outputs.py
```

Expected: FAIL missing `IP.China.ipv4.yaml`（或同类）——证明门禁生效。

- [ ] **Step 3: Commit**

```bash
git add scripts/validate_outputs.py
git commit -m "feat(scripts): add validate_outputs gate"
```

---

### Task 3: ChinaIP `fetch_and_collapse`

**Files:**
- Modify: `scripts/ChinaIP.py` (full rewrite)
- Optional Create: `tests/test_collapse.py`

- [ ] **Step 1: 写失败用例（推荐） `tests/test_collapse.py`**

```python
import ipaddress
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ChinaIP import collapse_cidrs, parse_cidr_lines  # type: ignore


def test_parse_skips_comments():
    lines = ["# c", "", "1.1.1.0/24", "not-a-cidr", "2001:db8::/32"]
    out = parse_cidr_lines(lines)
    assert "1.1.1.0/24" in [str(n) for n in out]
    assert any(str(n) == "2001:db8::/32" for n in out)
    assert not any(str(n) == "not-a-cidr" for n in out)


def test_collapse_merges_adjacent():
    nets = parse_cidr_lines(["1.1.1.0/25", "1.1.1.128/25"])
    collapsed = collapse_cidrs(nets)
    assert collapsed == ["1.1.1.0/24"]


if __name__ == "__main__":
    test_parse_skips_comments()
    test_collapse_merges_adjacent()
    print("ok")
```

- [ ] **Step 2: 跑测期望 FAIL（函数未定义）**

```bash
python tests/test_collapse.py
```

Expected: `ImportError` 或 `AttributeError`

- [ ] **Step 3: 重写 `scripts/ChinaIP.py`**

```python
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
```

- [ ] **Step 4: 再跑单测**

```bash
python tests/test_collapse.py
```

Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add scripts/ChinaIP.py tests/test_collapse.py
git commit -m "feat(scripts): ChinaIP fetch_and_collapse with multi-source union"
```

---

### Task 4: convert_formats 直调 + 分卷 yaml

**Files:**
- Modify: `scripts/convert_formats.py` (full rewrite)

- [ ] **Step 1: 重写 convert_formats.py**

```python
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
```

- [ ] **Step 2: 真网跑 convert（需网络）**

```bash
pip install -r requirements.txt
python scripts/convert_formats.py
ls -la IP.China.txt IP.China.yaml IP.China.ipv4.yaml IP.China.ipv6.yaml
```

Expected: 四个文件非空；stderr/stdout 有 collapse 前后 count。

- [ ] **Step 3: Commit**

```bash
git add scripts/convert_formats.py
git commit -m "feat(scripts): convert via fetch_and_collapse and split v4/v6 yaml"
```

---

### Task 5: ChinaASN 多 URL + 排序去重 + 原子写 + 可选 lxml

**Files:**
- Modify: `scripts/ChinaASN.py` (full rewrite)

- [ ] **Step 1: 重写 ChinaASN.py**

```python
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
```

- [ ] **Step 2: 真网跑**

```bash
python scripts/ChinaASN.py
head -20 ASN.China.list
```

Expected: exit 0；`payload:` 后 `- IP-ASN,<num>` 升序、无重复号。

- [ ] **Step 3: Commit**

```bash
git add scripts/ChinaASN.py
git commit -m "feat(scripts): harden ChinaASN multi-url sort dedupe atomic write"
```

---

### Task 6: CI 串行 + validate

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: 替换 workflow**

```yaml
name: Update ASN and IP List

on:
  push:
  workflow_dispatch:
  schedule:
    - cron: "0 16 * * *"

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install lxml

      - name: Fetch ASN
        run: python scripts/ChinaASN.py

      - name: Fetch IP and convert formats
        run: python scripts/convert_formats.py

      - name: Validate outputs
        run: python scripts/validate_outputs.py

      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "chore: update IP/ASN lists [automated]"
          file_pattern: "ASN.China.list IP.China.txt IP.China.yaml IP.China.ipv4.yaml IP.China.ipv6.yaml"
```

说明：`file_pattern` 排除已删除的中间 list；auto-commit 无变更则跳过。

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: serial ASN convert validate pipeline"
```

---

### Task 7: 删死代码与废弃 list 产物

**Files:**
- Delete: `scripts/IPlist_to_CIDR.py`
- Delete: `scripts/IPlist_to_yaml.py`
- Delete: `IP.China.list`
- Delete: `IPv4.China.list`
- Delete: `IPv6.China.list`

- [ ] **Step 1: 删除**

```bash
git rm scripts/IPlist_to_CIDR.py scripts/IPlist_to_yaml.py
git rm IP.China.list IPv4.China.list IPv6.China.list
```

- [ ] **Step 2: 确认无引用**

```bash
rg -n "IPlist_to_|IP\.China\.list|IPv4\.China\.list|IPv6\.China\.list" --glob '!docs/**' || true
```

Expected: 代码与 CI 无残留（README 在 Task 8 改干净）。

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove dead converters and intermediate IP list files"
```

---

### Task 8: README Clash 文档 + fork 身份

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 重写 README**

```markdown
# ASN-China-clash

High-cla fork of [missuo/ASN-China](https://github.com/missuo/ASN-China): daily China ASN + IP lists with **Clash/Mihomo** rule-provider outputs, CIDR collapse, and CI validation gates.

## Features

- Daily GitHub Actions update (UTC 16:00 schedule + manual dispatch)
- ASN from bgp.he.net (regex + optional lxml fallback, multi-URL via `ASN_URLS`)
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

```bash
pip install -r requirements.txt
# optional ASN fallback: pip install lxml
python scripts/ChinaASN.py
python scripts/convert_formats.py
python scripts/validate_outputs.py
```

Env: `REQUEST_TIMEOUT`, `USER_AGENT`, `MIN_ASN_COUNT` (default 100), `MIN_CIDR_COUNT` (default 1000).

## License

MIT (see [LICENSE](./LICENSE)). Original work (c) Vincent Young / missuo; this fork maintains Clash-oriented tooling.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: Clash usage and High-cla fork identity"
```

---

### Task 9: 端到端云端验证

- [ ] **Step 1: 开实现 PR**（分支 `opt-asn-clash`，基于 `main`；可把 docs 分支合并进来）

```bash
gh pr create --title "feat: ASN-China-clash full-tier optimization" --body "Implements docs/superpowers/specs/2026-07-21-asn-china-clash-optimization-design.md"
```

- [ ] **Step 2: `workflow_dispatch` 跑 Actions**

Expected:
- ChinaASN / convert / validate 全绿
- auto-commit 更新 5 个产物（或无 diff 跳过）
- 仓库中无 `IP.China.list` / `IPv4.China.list` / `IPv6.China.list` 新提交

- [ ] **Step 3: 抽查 raw 产物与日志**（ASN 升序、v4/v6 前缀、collapse before>after 通常成立）

- [ ] **Step 4: 用户确认后合并 PR**

---

## Spec coverage checklist

| Spec 项 | Task |
|---------|------|
| 多 URL ASN + regex + 可选 lxml | 5 |
| 排序去重 + 原子写 ASN | 1, 5 |
| IP 多源并集 + collapse | 3 |
| 不写 IP.China.list | 3, 7 |
| convert 直调 + txt/全量/v4/v6 yaml | 4 |
| validate 门禁 | 2, 6 |
| CI 串行 3.12 | 6 |
| 删死代码 | 7 |
| 删废弃 list | 7 |
| README Clash + fork | 8 |
| 空结果不写 / exit 1 | 3–5 |
| requirements 仅 requests；CI 可装 lxml | 6 |
| 不建 src/ | 全程 `scripts/` |

## Self-review notes

- 无 TBD；函数名统一 `fetch_and_collapse` / `atomic_write` / `validate_outputs.main`。
- v6 校验用 `startswith("IP-CIDR,") and not startswith("IP-CIDR6,")` 避免误伤。
- convert 在 v4 或 v6 为空时 exit 1（中国列表实网两者应非空）。
- 未强制 pytest；`tests/test_collapse.py` 可 `python tests/test_collapse.py` 裸跑。

---

*Plan complete. Execute via subagent-driven-development or executing-plans.*
