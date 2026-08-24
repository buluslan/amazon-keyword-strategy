# 通用输入层 Schema

定义 skill 的统一输入字段。所有数据源适配器把原生字段映射到本 schema；分析层只认本 schema，不认具体源。

> 核心原则：分析层只需「关键词」就能跑核心逻辑（词根分类 / 标品判别 / 匹配建议）。字段越多分析越精确；字段缺失则降级，但不停摆。

---

## 字段定义（权威表见 adapter-interface.md §一）

本文件不重复字段全表。**字段命名/结构以 `adapter-interface.md` §一为唯一真理源**，此处只列分组：

- **必填**：`keyword`（string）—— 唯一硬性要求。没关键词 = 没输入，skill 不跑。
- **强烈推荐**：`search_volume`（int）—— 驱动大中小词分层。缺失标 `[缺失]`。
- **选填增强**（有则填，缺失标 `[缺失]`）：
  - `aba_rank`（int）ABA 排名 → 搜索热度分层
  - `conversion_rate`（float）转化率 → 标品判别第三维度核心信号
  - `purchases`（int）月购买量 → 出单词集中度定量主方法（前5词单量占比）
  - `conversion_tag`（string）转化标签 E/S/L/I → 集中度定性次方法
  - `bid`（float）PPC 竞价 → 最稀缺字段，缺失属常态
  - `competition`（object）竞争指标 → 含 `click_concentration` / `conv_concentration` / `spr` / `products` / `supply_demand_ratio` / `ad_products` / `coverage`
  - `relevance`（object）相关性 → 含 `tier` / `score` / `coverage{top4,top8,top16,top32,top48}`（含占位率列的 xlsx 独家）
  - `trend`（object/string）趋势 → 阶段性标记
- `source_asin`（list[string]）反查来源 → 多竞品合并场景自动产生，语义与竞品覆盖数见 `adapter-interface.md` §五·五；词表输入无此字段

字段命名一律 **snake_case**；竞争/相关性指标归入 `competition` / `relevance` object（与 Python 适配器实现一致，不平铺）。

## 原始字段透传（留底铁律）

分析阶段**保留输入/适配器返回的全部原始字段**进 payload 的 keywords——判定字段（word_root / brand_role / match_type / action / stage / ppc_quadrant / aba_tier / competition_score / competition_level）是**增量标注，不是替换**：数值分档字段（aba_tier / competition_score / competition_level / ppc_quadrant）由 render 按固定界限计算覆盖，品牌双分类标记（`brand_role`：own 本品 / competitor 竞品 / eco 兼容生态，word-root-classification.md 品牌节）由 Agent 判断注入，但原始值本身（aba_rank / conversion_rate / bid / competition.* / relevance.* / 占位率各档）必须原样留在 keywords 里，不删、不改、不判完即丢。

**为什么**：数据过了这村没这店——原始指标是作战图「原始数据」sheet 留底的数据源，也是用户二次分析（换角度重新分档、复跑对比、导入其他工具）的唯一凭据。判定档位可以重算，原始值丢了就是丢了。

---

## 数据诚实三层

所有字段值必须落入三层之一（数据诚实护栏，**三层概念全文仅此一处定义**；各流程文件里的执行禁令——"不脑补/绝不编造"——是三层在各执行环节的就地钉死，不在此展开也不在此收编）：

| 标记 | 层级 | 含义 | 适用 |
|---|---|---|---|
| （无标记，直接数字）| 有数据 | 来自当前数据源的实测值 | 字段在源中存在且有返回 |
| `⏳` | 估算 | 源未返回，基于规则/经验推算 | 阶段性按搜索量规模推断（无趋势数据时标 ⏳） |
| `[缺失]` | 缺失 | 源不提供，分析降级 | 竞价 / 占位率等源没有的字段 |

估算标 `⏳` 并注明依据；缺失标 `[缺失]`——不填 0、不填均值。区分「有数据 / 估算 / 缺失」是输出可信度底线。

---

## 字段缺失 → 分析层降级映射

| 缺失字段 | 影响的分析 | 降级行为 |
|---|---|---|
| 无（仅 keyword）| — | 基础层全跑：词根分类 / 标品判别（维度1+2 定性）/ 匹配建议 / 否定词 |
| search_volume | 大中小词分层 / ABA 层级 | 分层跳过；有 aba_rank 时 ABA 层级仍按排名固定界限切档，无排名按本表搜索量分位兜底（均确定性） |
| competition | 竞争分 / 竞争强度 / 蓝海词 | 竞争分与强度标 `[缺失]`；蓝海词不输出 |
| conversion_rate | 出单词集中度 | 标品判别第三维度降级，转维度1（外观）+维度2（功能）两维度定性判别，标转化 `[缺失]` |
| bid | PPC 成本估算 | PPC 策略只给匹配类型建议，不出价 |
| trend | 阶段性标记 | 全部词标 `阶段[缺失]` |

降级不停摆——基础层（词根分类 / 标品判别 / 匹配建议）永不下线。

---

## 多源混合（可选增强）

用户同时有多个数据源时，可交叉验证取最优字段（**可选能力，需要时启用**）：

- 搜索量：多源取均值或更可信源，标注「多源均值」
- 竞争强度：可用指标等权进竞争分（公式见 battleplan-template.md §3.1，指标槽自动命中）
- 反查拉词：多源去重合并，词更全

混合时每个字段仍遵循数据诚实三层。

---

## 与适配器的关系

本 schema 只定义字段，不定义怎么取。各数据源适配器负责把原生字段映射到本 schema（映射表见 `adapter-interface.md`）。加新源 = 写一个适配器 + 注册表登记，不改本 schema。

> 输出侧：作战图 payload 的 `root_summary` / `campaign_groups` schema 以 `battleplan-template.md` §6 为准（本文件只管输入层字段）。
