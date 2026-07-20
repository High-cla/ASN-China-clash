# ASN-China-clash 完整档优化设计

**日期**: 2026-07-21  
**仓库**: [High-cla/ASN-China-clash](https://github.com/High-cla/ASN-China-clash)  
**上游对照**: [missuo/ASN-China](https://github.com/missuo/ASN-China)  
**范围**: 完整档 C（README + 死代码清理 + CI 空文件门禁 + ASN 解析加固/排序去重 + Clash 文档 + CIDR 聚合 + 分 v4/v6 yaml + 多数据源兜底）  
**操作约束**: 实现阶段以 GitHub 云端改仓库为主

---

## 1. 目标与非目标

### 1.1 目标

1. 在 High-cla fork 上继续增强，**不回退**到 missuo 的 lxml 主路径与无 Clash 产物形态。
2. 产出可直接用于 Clash/兼容客户端的规则集，并在 CI 中用真实抓取 + 校验门禁保证「空/半截产物不入库」。
3. 提升 ASN/IP 抓取韧性（超时、多 URL、解析回退、原子写）。
4. 对 IP 做 **stdlib `ipaddress` 聚合（collapse）**，减少规则条数。
5. 文档与 fork 身份对齐（说明本仓库相对 missuo 的差异与 Clash 用法）。

### 1.2 非目标

- 不新建 `src/` 包布局；**保持现有 `scripts/` 目录**（用户曾说「根目录小改」，以仓库现状 `scripts/` 为准，不迁目录、不扩成多包结构）。
- 不把实现迁回 missuo 的 `ASN_CN.py` / `IP_CN.py` 主逻辑。
- 不引入第二套规则引擎 / 代理内核格式全家桶（仅维护当前 txt + Clash payload yaml 形态）。
- 不在本阶段做多云镜像、CDN、或非 GitHub Actions 的发布管道。

---

## 2. 现状基线（实现须对照）

| 路径 | 现状 | 设计后 |
|------|------|--------|
| `scripts/ChinaASN.py` | 单 URL、regex、空则不写；写出含 `payload:` 的 ASN list | 多 URL 顺序尝试 + regex 主路径 + 可选 lxml 回退；排序去重；原子写 |
| `scripts/ChinaIP.py` | 直接下载 3 个 cbuijs 文件到 `IP.China.list` / `IPv4.China.list` / `IPv6.China.list` | 多源并集 → collapse → **不落盘中间 list**；暴露 `fetch_and_collapse() -> list[str]` |
| `scripts/convert_formats.py` | 读 `IP.China.list`，写 `IP.China.txt` + `IP.China.yaml`；空 list 时 exit 0 仍可能放过 | 直调 ChinaIP；写 txt + 全量 yaml + ipv4/ipv6 yaml；空则失败不写 |
| `scripts/IPlist_to_CIDR.py` / `IPlist_to_yaml.py` | 死代码 | **删除** |
| `.github/workflows/ci.yml` | Python 3.12；ChinaIP∥ChinaASN 并行；弱校验（`wc`/`head`） | **同 job 串行**；强 `validate_outputs`；通过才 auto-commit |
| `README.md` | 仍指 missuo raw / Surge·QX | 改为本 fork raw + **Clash 用法** + 产物说明 |
| 根目录产物 | `ASN.China.list`, `IP.China.list`, `IPv4/6.China.list`, `IP.China.txt`, `IP.China.yaml` | 见 §3 |

---

## 3. 产物契约

### 3.1 继续维护（CI 提交）

| 文件 | 格式要点 |
|------|----------|
| `ASN.China.list` | 注释头 + `payload:` + `- IP-ASN,<num>` 行；条目排序、按 ASN 号去重 |
| `IP.China.txt` | 每行 `IP-CIDR,<cidr>,no-resolve` 或 `IP-CIDR6,<cidr>,no-resolve` |
| `IP.China.yaml` | `payload:` + 缩进 `- IP-CIDR...` / `- IP-CIDR6...` |
| `IP.China.ipv4.yaml` | 仅 IPv4 的 payload yaml |
| `IP.China.ipv6.yaml` | 仅 IPv6 的 payload yaml |

### 3.2 停止作为流水线产物写入

- `IP.China.list`：**不写**（用户确认）；转换走内存/`fetch_and_collapse()`。
- `IPv4.China.list` / `IPv6.China.list`：**停止更新**。若仓库中已有历史文件，实现 PR 可选择删除或保留最后一次内容并在 README 标明废弃；默认倾向 **删除**，避免与 yaml 分卷双源漂移。

### 3.3 空结果与半截文件

- 任一必需产物在「应生成却为空/无有效条目」时：**不写该文件**（保留旧文件或使之缺失，由 validate 判定）。
- 写盘一律：`*.tmp` → 校验非空 → `os.replace` 原子替换。
- 抓取/解析/转换失败：进程 **exit 1**；CI 不 auto-commit。

---

## 4. 组件设计

### 4.1 `scripts/ChinaASN.py`

**职责**: 抓取中国 ASN 并写出 `ASN.China.list`。

**流程**:

1. 读取 `ASN_URLS`（默认含 `https://bgp.he.net/country/CN`，可环境变量逗号分隔扩展）。
2. 按序请求：`REQUEST_TIMEOUT`、`USER_AGENT`；失败则下一 URL。
3. 解析：
   - **主路径**: 现有风格 regex（匹配 AS 号与名称列）。
   - **回退**: 若已安装 `lxml` 且 regex 结果为空，再用 XPath/表格解析（可选依赖，失败不阻断「全失败」以外的逻辑）。
4. 规范化：`(asn_number, name)` → 按 ASN 数字排序；同 ASN 去重（保留首次非空 name）。
5. 非空则 **一次拼完整内容** 后原子写（禁止「先截断再 append」）；空则不写并 exit 1（CI 侧由 validate 双重保险）。

**输出格式**（保持 Clash payload 风格，与当前 fork 一致，**不**改回 missuo 的 `IP-ASN,N // 名称` 单行注释风格）:

```text
# ... header / Last Updated ...
payload:
- IP-ASN,4134
- IP-ASN,4837
```

名称字段：当前文件体不含名称；若后续要加注释行，须另开变更。本设计 **保持现有仅 ASN 号** 的 payload 行，排序去重即可。

### 4.2 `scripts/ChinaIP.py`

**职责**: 多源拉取中国 IP 前缀，合并、校验、collapse。

**API**:

```python
def fetch_and_collapse() -> list[str]:
    """Return sorted collapsed CIDR strings (v4+v6 mixed). Raise or return [] on total failure."""
```

**流程**:

1. `IP_SOURCES`：默认可配置列表；默认至少包含 cbuijs 全量/分卷源中与现状等价的集合（实现时以「能覆盖现网规模」为准，默认主源 cbuijs）。
2. **多源策略 = 去重并集**（用户确认）：每个源成功的行加入集合；单源失败记日志，不单独导致整体失败，**全部源失败**才失败。
3. 过滤非法行（注释、空行、无法被 `ipaddress.ip_network(..., strict=False)` 解析的行）。
4. `ipaddress.collapse_addresses` 聚合。
5. 返回 `list[str]`（规范化 CIDR 字符串）。
6. **CLI `python scripts/ChinaIP.py`**: 可打印条数到 stdout/stderr；**默认不写 `IP.China.list`**。若需调试写盘，仅允许显式 flag（可选，非必须）。

### 4.3 `scripts/convert_formats.py`

**职责**: 一次生成全部 IP 规则产物。

**流程**:

1. `from ChinaIP import fetch_and_collapse`（同目录导入；CI 在仓库根运行时用 `python scripts/convert_formats.py` 并保证 `sys.path` 含 `scripts/`，或改为相对导入包装——实现时选一种并在 plan 写死）。
2. 若列表空 → exit 1，不写任何输出。
3. 拆分 v4 / v6（`:` 判定或 `ip_network.version`）。
4. 原子写：
   - `IP.China.txt`
   - `IP.China.yaml`
   - `IP.China.ipv4.yaml`
   - `IP.China.ipv6.yaml`
5. 行格式与现网一致：`IP-CIDR` / `IP-CIDR6` + `,no-resolve`；yaml 带 `payload:` 与两空格缩进 `- `。

### 4.4 `scripts/validate_outputs.py`（新建）

**职责**: 只读校验，失败 exit 1。

**检查项**（阈值可用环境变量覆盖）:

| 检查 | 默认 |
|------|------|
| 必需文件存在 | `ASN.China.list`, `IP.China.txt`, `IP.China.yaml`, `IP.China.ipv4.yaml`, `IP.China.ipv6.yaml` |
| 非空 | 每个必需文件 size > 0 |
| ASN 有效 payload 行数 | ≥ `MIN_ASN_COUNT`（默认 100） |
| 全量 CIDR 条数（txt 或 yaml 解析） | ≥ `MIN_CIDR_COUNT`（默认 1000） |
| yaml | 含 `payload:`；条目以 `IP-CIDR`/`IP-CIDR6`/`IP-ASN` 之一为前缀 |
| v4 yaml | 无 `IP-CIDR6` 条目 |
| v6 yaml | 无 `IP-CIDR`（v4）条目 |

### 4.5 CI（`.github/workflows/ci.yml`）

- 触发: `schedule`（保持现有 cron 或等价日更）、`workflow_dispatch`；`push` 是否保留：实现时 **保留 push 触发但 auto-commit 仅在数据更新时**，避免文档-only push 死循环（`git-auto-commit` 无变更则空提交跳过）。
- Python **3.12**。
- **同 job 串行**（用户确认）:

```text
checkout → setup Python → pip install -r requirements.txt
→ python scripts/ChinaASN.py
→ python scripts/convert_formats.py   # 内部调 ChinaIP.fetch_and_collapse
→ python scripts/validate_outputs.py
→ git-auto-commit（仅当有变更）
```

- 不再并行 ChinaIP∥ChinaASN 再 convert 读盘（消除对中间 list 的依赖与竞态）。
- 可选：`ChinaIP.py` CLI 不再作为 CI 独立步骤（逻辑并入 convert）。

### 4.6 依赖（`requirements.txt`）

- 必选: `requests`（钉版本或兼容范围，实现时沿用/微调）。
- 可选: `lxml` — **不强制写入 requirements**；若写入则为 ASN 回退提供保障。设计推荐：**requirements 仅 requests**；文档说明 `pip install lxml` 可启用 ASN 解析回退。若希望 CI 稳定回退，可在 CI 步骤额外 `pip install lxml` 而不污染最小依赖。

### 4.7 README

- 声明本仓库为 High-cla fork，说明相对 missuo 的差异（Clash yaml/txt、聚合、门禁）。
- raw URL 全部改为 `https://raw.githubusercontent.com/High-cla/ASN-China-clash/main/...`。
- **Clash / Mihomo** 示例：`rule-providers` 引用 `IP.China.yaml` 或分卷 ipv4/ipv6；可选 `ASN.China.list` 若客户端支持。
- 保留或降级提及 Surge/QX，但不再主推 missuo 链接作为本仓库数据源。
- 数据源表：ASN（bgp.he.net 等）、IP（cbuijs + 可配置备源说明）。

### 4.8 删除

- `scripts/IPlist_to_CIDR.py`
- `scripts/IPlist_to_yaml.py`

---

## 5. 配置面（环境变量）

| 变量 | 含义 | 默认 |
|------|------|------|
| `ASN_URLS` | 逗号分隔 ASN 页面 URL | `https://bgp.he.net/country/CN` |
| `IP_SOURCES` | 逗号分隔 IP 列表 URL | cbuijs 默认集合（实现 plan 写死具体 URL 列表） |
| `REQUEST_TIMEOUT` | 秒 | `30` |
| `USER_AGENT` | HTTP UA | 现有 Chrome UA 字符串 |
| `MIN_ASN_COUNT` | validate | `100` |
| `MIN_CIDR_COUNT` | validate | `1000` |

无配置文件；默认可直接跑 CI。

---

## 6. 数据流

```text
[ASN_URLS] --HTTP--> ChinaASN (regex → optional lxml)
                         |
                         v  (non-empty, sorted unique)
                   ASN.China.list

[IP_SOURCES] --HTTP--> ChinaIP (union + parse + collapse)
                         |
                         v  list[str] in memory
                   convert_formats
                         |
         +---------------+---------------+----------------+
         v               v               v                v
   IP.China.txt   IP.China.yaml   IP.China.ipv4.yaml  IP.China.ipv6.yaml

validate_outputs (read-only) --> exit 0/1 --> auto-commit if changed
```

---

## 7. 错误处理

| 场景 | 行为 |
|------|------|
| 单 ASN URL 失败 | 试下一个 |
| 全部 ASN URL 失败或解析 0 条 | 不写 ASN 文件，exit 1 |
| 单 IP 源失败 | 跳过，合并其余 |
| 全部 IP 源失败或 collapse 后 0 条 | 不写 IP 产物，exit 1 |
| validate 不通过 | exit 1，不 commit |
| 写盘中途异常 | 不 `replace` 正式文件，exit 1 |

---

## 8. 测试策略

| 层级 | 内容 | 是否必须 |
|------|------|----------|
| 可选单元 | fixture HTML/文本测 regex 解析、collapse 输入输出 | 推荐但非阻塞 |
| CI 集成 | 真网抓取 + `validate_outputs` | **必须** |

不在本设计强制引入 pytest 基础设施；若加单测，文件放 `scripts/tests/` 或 `tests/`，plan 阶段再定。

---

## 9. 成功标准

1. CI 日更：`validate_outputs` 通过后才提交。
2. 人为制造空抓取时，仓库不会被空文件覆盖。
3. `IP.China.yaml` 与分卷 yaml 可被 Clash/Mihomo `rule-providers` 直接引用（README 有可复制片段）。
4. 死代码脚本已删除；README 无 missuo 作为本仓库 raw 主链。
5. IP 条数相对 collapse 前有可观测下降（日志打印 collapse 前后 count）。

---

## 10. 实现分期（供 writing-plans 拆分）

1. **清理 + 门禁骨架**: 删死代码；加 `validate_outputs.py`；CI 串行接上 validate（可先仍读现有中间 list）。
2. **ChinaIP 重构**: `fetch_and_collapse`、多源并集、不写 list；convert 直调；分卷 yaml。
3. **ChinaASN 加固**: 多 URL、排序去重、原子写、可选 lxml。
4. **README + 废弃产物**: 文档、删除/停更旧 list、确认 auto-commit 无环。

---

## 11. 已拍板决策记录

| # | 决策 | 选择 |
|---|------|------|
| 1 | 优化档位 | 完整档 C |
| 2 | 代码布局 | 保持 `scripts/`，不建 `src/` |
| 3 | ASN 解析 | regex 主 + 可选 lxml 回退 + 多 URL |
| 4 | IP 多源 | **去重并集合并** 后 collapse |
| 5 | `IP.China.list` | **不写文件** |
| 6 | 空结果 | **不写文件** + validate 失败 |
| 7 | CI 并行度 | **同 job 串行** |
| 8 | ChinaIP↔convert | `fetch_and_collapse()` 直调 |
| 9 | 聚合库 | stdlib `ipaddress` only |
| 10 | IP 默认源 | cbuijs；`IP_SOURCES` 可扩展 |

---

## 12. 风险与缓解

| 风险 | 缓解 |
|------|------|
| bgp.he.net 改版导致 regex 失效 | lxml 回退 + 多 URL 配置位 + validate 下限 |
| cbuijs 短暂 404 | 多源并集；全失败才挂 |
| collapse 行为与「原样转发 list」消费者差异 | README 说明已聚合；保留 txt/yaml 同源 |
| auto-commit 与 push 触发循环 | auto-commit 无变更跳过；commit message 固定前缀可过滤 |
| `scripts` 导入路径 | plan 中固定一种（`sys.path.insert` 或 `-m`） |

---

*本文件为 brainstorming 产出之设计规格。用户审阅通过后，进入 writing-plans 编写实现计划，再云端实施。*
