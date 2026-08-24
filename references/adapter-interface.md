# 适配器接口规范 · Adapter Interface

数据源层与通用输入层之间的契约。每个数据源实现统一 ABC，注册进工厂；分析层只认通用 schema，不感知具体源。

> 配套阅读：`generic-schema.md`（通用字段定义）、SKILL.md「关键原则 · 数据源不绑定」。

---

## 一、通用 Schema 字段

分析层只认这些字段。缺就标 `[缺失]`，不脑补。

| 字段 | 类型 | 必填 | 用途 |
|---|---|---|---|
| `keyword` | string | ✅ | 词根分类/标品判别/匹配建议的唯一下限 |
| `search_volume` | int | 选填 | ABA 层级分层（大/中/小词） |
| `aba_rank` | int | 选填 | 流量阈值分档 |
| `competition` | object | 选填 | 竞争强度（集中度/SPR/商品数等多个子字段） |
| `bid` | float | 选填 | PPC 策略建议 |
| `conversion_rate` | float | 选填 | 出单词集中度判别（标品/非标品核心信号） |
| `purchases` | int | 选填 | 月购买量（出单词集中度辅助信号） |
| `conversion_tag` | string | 选填 | 转化类型标签（源枚举透传，如 E/S/L/I；未定义值原样透传不解读） |
| `trend` | object | 选填 | 阶段性标记（新品/成长/成熟/衰退） |
| `relevance` | object | 选填 | 相关性（SIF 独家口径，源无则自算共性占位率） |
| `source_asin` | list[string] | 选填 | 该词来自哪些反查 ASIN（多竞品合并场景，`normalize_to_schema(source_asin=...)` 逐批写入；词表输入无此 key） |

**下限**：只有 `keyword` 时，词根分类 + 标品判别（走主观提示分支）+ 匹配建议照跑，增强层标 `[缺失]`。

---

## 二、KeywordFetcher ABC

所有数据源适配器实现以下 4 方法。路径 `scripts/keyword_fetchers/base.py`。

```python
from abc import ABC, abstractmethod

class KeywordFetcher(ABC):
    """数据源适配器抽象基类。"""

    @abstractmethod
    def fetch(self, asin: str, marketplace: str, **kwargs) -> list[dict]:
        """反查拉词，返回通用 schema 的词表 JSON（list[dict]，每 dict 一词）。
        字段缺失的 key 不要凭空造，直接缺。"""

    @abstractmethod
    def list_fields(self) -> list[str]:
        """声明本源能提供的通用 schema 字段名（如 ['keyword','search_volume','competition']）。
        分析层据此决定哪些增强逻辑可跑、哪些标 [缺失]。"""

    @abstractmethod
    def validate_config(self) -> bool:
        """探测本源在当前环境是否可用（MCP 工具存在/凭证有效/文件可读）。
        返回 True/False，不抛异常——失败由上层走降级。"""

    @abstractmethod
    def get_name(self) -> str:
        """返回源标识（如 'sif_xlsx'），用于日志和作战图注明数据来源。"""
```

**约定**：
- `fetch` 返回的每个 dict 至少含 `keyword`，其他字段按源能力给，给不出就不写该 key。
- 数值字段不要填 `0` 冒充缺失——缺 key 才是缺失，`0` 是真实值。
- 异常在 `validate_config` 拦住；`fetch` 自身不再 try/except 吞错，交给上层统一降级。

---

## 三、注册表 + 工厂（文件源）

路径 `scripts/keyword_fetchers/registry.py`。**只有文件源注册为 Python 适配器**：

```python
FETCHER_REGISTRY = {
    "sif_xlsx": SifXlsxFetcher,   # 含占位率/相关性列的 xlsx
    "csv":      CsvFetcher,       # 通用 csv 词表
}

def get_fetcher(name: str, **kwargs) -> KeywordFetcher:
    """按名称取文件适配器实例。"""

def detect_file_fetcher(filepath: str) -> KeywordFetcher | None:
    """按文件后缀自动选适配器，返回 validate_config 通过的实例；不可识别返回 None。"""
```

加新文件源 = 新建 fetcher 文件 + 注册表加一行。

### MCP 源（不在 Python 适配器，走两层）

⚠️ MCP 工具（如 traffic_keyword）是 **Agent 工具，Python 不能直接调**。MCP 源走两层：
1. Agent 按 SKILL.md Step 1 调 MCP 拿原始关键词数据
2. Agent 调 `scripts/parse_input.py` 的 `normalize_to_schema(raw_items, source='mcp')` 标准化到通用 schema

MCP 源**不**写成 Python `KeywordFetcher` 子类（代码里不存在 SellerspriteFetcher / SifMcpFetcher）。文件源 + MCP 源最终都产出通用 schema `list[dict]`，分析层无感知差异。这是本 skill 与 review-analyzer 的关键区别（review 的 Python 直接调 API；本 skill 的 MCP 数据由 Agent 取后标准化）。

---

## 四、各源字段映射表

映射方向：**源原生字段 → 通用 schema 字段**。分析层只读通用 schema。

### 4.1 可用 MCP 源（以 traffic_keyword 为主接口）

反查用 `keyword_order`（传 ASIN 拉词），字段填充用 `traffic_keyword`（传 ASIN 拉其流量词 + 指标），趋势用 `aba_research_trend`。

| 通用 schema | 原生字段 | 来源接口 |
|---|---|---|
| `keyword` | 关键词文本 | `keyword_order` / `traffic_keyword` 返回 |
| `search_volume` | `searches` | `traffic_keyword` |
| `aba_rank` | `searchesRank` | `traffic_keyword` |
| `competition` | `monopoly_click_rate` + `SPR` + `products` + `supplyDemandRatio` | `keyword_miner` / `traffic_keyword` |
| `bid` | `bid` | `traffic_keyword` / `keyword_miner` |
| `conversion_rate` | `purchaseRate` | `traffic_keyword` / `keyword_miner` |
| `purchases` | `purchases`（月购买量）| `traffic_keyword` / `keyword_miner` |
| `conversion_tag` | `conversionType`（E/S/L/I 转化标签；实测另见 U 等未定义值，原样透传不解读）| `keyword_order` |
| `trend` | 时序数据 | `aba_research_trend` / `keyword_research_trends` |
| `relevance` | `[缺失]`（无占位率概念） | 需自算共性占位率 = 词出现于反查竞品数 / 总竞品数 |

> 点击集中度在该源用 `monopoly_click_rate` 近似，不等同 SIF 的 Top3 口径，分析层注意标注口径差异。
> `keyword_order` 反查返回里另有驼峰原生 key `top3ClickingRate` / `top3ConversionRate`（Top3 点击/转化集中度），`normalize_to_schema` 已映射到 `competition` 对应子键。

### 4.2 SIF MCP（语义字段参考 ⏳）

字段名为语义推断，接入时以该源实际返回的 key 为准。

| 通用 schema | SIF MCP 语义字段 | 接口 ⏳ |
|---|---|---|
| `keyword` | 反查返回关键词 | `market_get_asin_keyword_signals` ⏳ |
| `search_volume` | 搜索量 | `market_get_keyword_demand` ⏳ |
| `aba_rank` | `rank_evolution` | ⏳ |
| `competition` | `coverage_ratio` + `top3_click_share` | `market_get_keyword_competition` ⏳ |
| `bid` | `[缺失]` | SIF MCP 能力边界明确无竞价 |
| `conversion_rate` | `top3_conversion_share` | ⏳ |
| `trend` | `overall_trend` / `market_get_keyword_history` | ⏳ |
| `relevance` | `coverage_ratio`（占位率语义，SIF 独家） | ⏳ |

> ⏳ = 语义推断字段，接入后以实际返回为准确认。

### 4.3 SIF 网页 xlsx

以实际文件列为准（下列为已确认的 15 列；个别列可能随平台版本变化，解析时按列名嗅探，不写死列序）。

| 通用 schema | xlsx 列名（实测） | 说明 |
|---|---|---|
| `keyword` | 关键词 | |
| —（透传） | 中文翻译 | 无通用 schema 对应，原样保留 |
| `relevance` | 相关性(高/中/低/几乎不) + 相关性得分(0-100) | SIF 独家双口径 |
| `search_volume` | 周搜索量 | 注意是周维，分析层换算 |
| `aba_rank` | ABA排名 | |
| `conversion_rate` | 24h点击转化率 | |
| `bid` | 建议竞价(低/中/高) | 三档，取中位或拆存 |
| `competition` | Top3点击集中度 + Top3转化集中度 | |
| `relevance`（占位口径） | Top4/Top8/Top16/Top32/Top48 占位率（5档） | SIF 独家，0-1 数值 |
| `trend` | `[缺失]` | xlsx 是快照，无时序 |

> 相关性阈值（滑块可调）：高(60-100%] / 中(20-60%] / 低(2-20%] / 几乎不[0-2%]。分析层默认用此分档。
> ⚠️ 适配器默认只读 active sheet——源导出的多分类 sheet 词表由 Agent 显式逐个读取挖掘（SKILL.md Step 1 同款提示），勿静默丢弃。

---

## 五、探测逻辑（取数类，钉死）

SKILL Step 1 出词按以下顺序，不得跳步、不得脑补：

1. 按注册表顺序逐个 `validate_config`。
2. 命中可用源 → 调 `fetch` 反查 → 拿词表 JSON → 进 Step 2。
3. 全部不可用 → **提示用户上传词表**（xlsx/csv/粘贴），不编造关键词。
4. `fetch` 返回空词表（源可用但该 ASIN 查不到词）→ 同第 3 步，明示"反查为空，请上传词表"。

> 钉死点：数据源不可用 / 反查为空时，必须走降级提示，绝不返回编造的词。这是数据诚实底线。

---

## 五·五、多竞品反查合并（新品建库场景）

`fetch(asin)` 签名不变，仍是单 ASIN 反查。用户给**竞品 ASIN 列表（1~5 个）**时，Agent 循环逐个反查后合并：

1. 每个竞品反查的原始数据单独过 `normalize_to_schema(raw, source='mcp', source_asin=B0XXX)`——本批每词写入单元素 `source_asin` 数组。
2. 全部批次汇总后过 `dedup()`：同词合并字段（取首个非空值），`source_asin` 数组拼接去重。
3. 合并结果 = 候选词池，进 Step 2 分析。

**source_asin 数组语义**：数组长度 = 该词被几个竞品的反查命中 = **竞品覆盖数**（多数竞品都在出的词 = 品类共性需求，个别竞品独有的词需甄别是否其关联流量）。这与 SIF 类工具的「共性占位率」（词出现于反查竞品数 / 总竞品数）同概念——数据结构天然支持，分析层可按需引用；本版不单独成列，留在 json 与原始数据 sheet。

**核心关键词锚**（用户提供了时）：框定品类边界——反查结果中与核心词语义无关的词族按可疑处理（降观察 / 问用户），防个别竞品的关联流量把候选池带偏。

---

## 六、数据源不绑定原则

- SKILL.md 全文写「可用数据源」「适配器按环境切换」，**不写具体源名**作为执行依赖。
- 本文件列出各源字段映射，是给适配器实现者看的参考，不等于 SKILL 绑定某源。
- 用户环境有什么源，就适配什么源；没有源就降级到词表上传。
- 加新源不改分析层、不改 SKILL.md，只在适配器层扩展。

---

## 七、加新源步骤

1. 新建 `scripts/keyword_fetchers/<新源>_fetcher.py`，继承 `KeywordFetcher`，实现 4 方法。
2. 在 `FETCHER_REGISTRY` 加一行 `"新源": NewSourceFetcher`。
3. 在本文件「字段映射表」补一节，列原生字段 → 通用 schema 映射。
4. `validate_config` 写好环境探测（MCP 工具存在性 / 凭证 / 文件可读性）。

分析层零改动——它只读通用 schema。

---

## 八、多源混合（可选增强）

同时有多个源时，可交叉验证取最优字段：
- 搜索量：多源取均值或取主源。
- 竞争强度：跨源指标交叉（如点击集中度 vs 占位率）。
- 反查：多源去重，词更全。

可选能力。需要时在工厂之上加一层 `MultiSourceFetcher`，合并多源 `fetch` 结果按字段优先级取值。
