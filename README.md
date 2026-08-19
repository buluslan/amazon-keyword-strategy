<div align="center">

<img src="assets/banner.png" alt="amazon-keyword-strategy" width="100%">

# 🎯 amazon-keyword-strategy

**把 ASIN 或关键词表,转成可执行的广告作战图,每个词都带打法:主攻、截流还是否定**

**想了解更多最新AI行业动态,AI+电商/广告的行业实践方法,人与AI如何协作共生的思考,请关注公众号:【新西楼.AI】**

![qrcode_for_gh_e3b954bd3859_258](https://github.com/user-attachments/assets/d8f068d9-c4f8-46c7-914c-fbcab5d52f2a)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.3.2-black.svg)]()

**标品/非标品分治 · 词根六分类 · 品牌双分类 · PPC 四象限 · 数据源无关 · 永不停摆**

**Created By Buluu@新西楼.AI**

</div>

---

## 项目简介

由 **buluslan（公众号:新西楼.AI）** 研发的亚马逊关键词库搭建 + 打法分析 Skill。你输入**竞品 ASIN**（新品建库）、**本品 ASIN**（老品诊断）、**单个竞品 ASIN**（竞品拆解），或**一份关键词表**（词表深加工），Skill 自动反查出词 → 标品/非标品判别 → 词根六分类，把几百个关键词变成一份可执行作战图——**每个词都带打法（主攻 / 截流 / 否定）**，区别于一次性关键词报告的数据罗列。数据源无关：没有数据源时上传词表照样跑。

一个 **Agent 通用** 的 Skill：输入 ASIN 或关键词表，输出带打法决策的作战图——不止给数据，给打法。

- **Agent 通用**：适配任意 Agent（Claude Code / Codex / Cursor / OpenCode 等），装上即用
- **数据源无关**：适配器架构，不绑定任何数据服务商；没有数据源时上传词表照样跑
- **永不停摆**：核心打法逻辑只需关键词本身就能出，搜索量/竞争度是增强字段，缺失标 `[缺失]` 绝不脑补

### 它解决什么问题

- ❌ 关键词工具给的是"词 + 数据"，几百个词甩在脸上，**哪些打、怎么打、什么阶段打**还是没头绪
- ❌ 否定词靠感觉拍，接口不匹配的配件词没否定干净，预算烧在不会转化的流量上
- ❌ 品牌词一刀切当竞品截流——**自有品牌词被截流等于放弃核心流量**（卖品牌产品时品牌词占词库大头）
- ❌ 标品和非标品打法混用：标品吃出单词集中打法、非标品吃长尾铺词，判错方向全盘皆输

## ✨ 它做什么

| 能力 | 说明 |
|---|---|
| **反查出词** | 输入 ASIN 自动拉 200-500 个关键词 + 搜索量/竞争度/转化/竞价字段（经适配器，按环境可用数据源切换）|
| **标品/非标品判别** | 出单词集中度 + 外观相似度 + 功能性三维度判别，定调后续全部打法 |
| **词根六分类** | 每个词归入共性/属性/品牌/品类/受众/否定，分类驱动匹配类型和动作 |
| **品牌双分类** | 本品品牌词 → 主攻；竞品品牌词 → 截流。两者打法相反，混判是高频踩坑 |
| **否定词识别** | 四类信号：语义不相关 / 前台跑偏 / 转化极低 / **接口/规格不匹配的配件词**（看着相关其实买本品的人用不上）|
| **PPC 四象限** | 搜索量 × 竞争强度分蓝海主攻 / 精准控预算 / 长尾广泛 / 不建议打，落到匹配类型和预算倾向 |
| **作战图三件套** | `作战图.xlsx`（精准词表+否定词表+PPC 策略）+ `作战图.md`（可读总结）+ `词表.json`（结构化数据）|

**说一句就能触发**：

```
帮我搭 B0D7FVQ1ZB 这个 ASIN 的关键词库
```
```
这 800 个词帮我分下类，哪些该否定
```
```
这个品是标品还是非标品？词表有了怎么打
```

## 🧠 打法方法论

### 词根六分类

每个词在广告里扮演什么角色，六类正交、每词归一类，分类驱动打法：

| 词根 | 判断标准 | 广告用途 |
|---|---|---|
| 共性词 | 产品最基础叫法，绝大多数同类 ASIN 都含 | 必须覆盖，广泛+词组+精准分层 |
| 属性词 | 修饰规格/特性/功能，能与共性词组合 | 精准投放，"小词带大词"核心载体 |
| 品牌词 | 专有名词——**先分本品还是竞品**（见下） | 本品主攻 / 竞品截流 |
| 品类词 | 同类产品的其他叫法/上位词 | 广泛覆盖 |
| 受众词 | 用户身份/使用场景/人群标签 | 精准首选 + 人群定向 |
| 否定词 | 不相关/跑偏/低转化/接口不匹配 | **直接进否定词表，不入词表** |

### 品牌词双分类（高频踩坑点）

| 子类 | 判定 | 处理 |
|---|---|---|
| **本品品牌** | = 你的 ASIN 厂商品牌（含变体） | **主攻**——自有品牌词是核心流量，归共性/属性处理 |
| **竞品品牌** | 词库中专有名词 ≠ 本品品牌 | **截流**——精准投放，独立广告组，单独预算 |

卖品牌产品时品牌词占词库大头，全截流等于放弃核心流量。词库中某品牌词频次显著高于其他品牌词，优先怀疑是本品品牌。

### 标品 / 非标品三维度

| 维度 | 看什么 |
|---|---|
| 出单词集中度 | 少数词出多数单 = 标品；几百词各出几单 = 非标品——**看转化数据分布，不是搜索量分布** |
| 外观相似度 | 搜索结果产品长得像不像 |
| 功能性 | 功能导向（标品倾向）vs 外观/风格导向（非标品倾向） |

## 🚀 快速开始

**安装**（Claude Code skills 路径；Codex / Cursor 用户把 SKILL.md 当指令喂给 agent 即可）：

```bash
git clone https://github.com/buluslan/amazon-keyword-strategy.git ~/.claude/skills/amazon-keyword-strategy
```

唯一 Python 依赖（渲染 xlsx 用）：

```bash
pip install openpyxl
```

**四种玩法任选**（同一个分析引擎，按"ASIN 是谁的"分流）：

| 你手里有什么 | 场景 | 说明 |
|---|---|---|
| 几个竞品 ASIN + 核心关键词 **新品建库** | 逐个反查合并成候选词池 → 分主攻/截流/否定，标出新品期先打哪些词 |
| 自己在售的 ASIN | **老品诊断** | 看自己实际吃什么词 → 否定止血、词结构体检 |
| 一个卖得好的竞品 ASIN | **竞品拆解** | 拆它的核心词体系，看能不能切 |
| 词表文件（xlsx/csv）或粘贴的关键词 | **词表深加工** | 零依赖纯关键词也能出基础作战图；有搜索量/竞争列自动进增强层 |

ASIN 反查需环境有数据源工具（适配器自动探测）；产物落盘在 `output/{ASIN}_{日期}/`。

## 🔌 数据源（不绑定）

适配器架构：加新数据源 = 加一个适配器文件 + 注册表一行，核心逻辑不动。

- 有数据源工具 → 自动反查拉词 + 填充增强字段
- 没有 → 提示上传词表，**绝不脑补关键词**
- 字段缺失 → 降级跑基础层，缺失标 `[缺失]`，未实测标 `⏳`

## 🎁 接入福利

接入数据源工具时，用以下 buluslan（公众号:新西楼.AI）专属优惠码享折扣（下单时在「折扣券」处粘贴对应码）：

| 工具 | 优惠码 | 折扣 | 购买链接 |
|------|--------|------|----------|
| 卖家精灵 · MCP | `XXL` | 9 折 | [open.sellersprite.com/pricing/mcp](https://open.sellersprite.com/pricing/mcp) |
| 卖家精灵 · 会员 | `XXL90`（包月）/ `XXL72`（单人包年）/ `XXL78`（标准/高级/VIP 包年） | 见官网对应套餐 | [sellersprite.com/cn/price](https://www.sellersprite.com/cn/price) |
| SIF · 会员 | `MBGAI` | 新购/增购/升级 88 折，续费 86 折 | [sif.com](http://www.sif.com/) |
| SIF · MCP | `MBGAI` | 88 折 | [sif.com](http://www.sif.com/) |

> 本 skill 与两家工具的数据都打通：**SIF 导出的关键词表（xlsx）可直接导入**（「词表深加工」场景，含占位率/相关性列自动识别）；**卖家精灵环境配了 MCP 时适配器自动探测反查**（「新品建库 / 老品诊断 / 竞品拆解」场景）。

<div align="center">
<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/c46f6725-4ebd-49a0-a6be-a4fc910465be" alt="卖家精灵优惠" width="240"></td>
    <td><img src="assets/sif-membership.png" alt="SIF 会员优惠" width="240"></td>
    <td><img src="assets/sif-mcp.png" alt="SIF MCP 优惠" width="240"></td>
  </tr>
  <tr>
    <td align="center"><b>卖家精灵</b></td>
    <td align="center"><b>SIF 会员</b></td>
    <td align="center"><b>SIF MCP</b></td>
  </tr>
</table>
</div>

## 📁 结构

```
amazon-keyword-strategy/
├── SKILL.md                  # 路由心脏（工作流 + 边界 + references 索引）
├── references/               # 按需加载的规则文档
│   ├── generic-schema.md     # 通用输入 schema（数据源无关的字段定义）
│   ├── adapter-interface.md  # 适配器接口规范 + 字段映射
│   ├── standard-vs-nonstandard.md
│   ├── play-analysis-engine.md
│   ├── word-root-classification.md
│   └── battleplan-template.md
├── scripts/
│   ├── keyword_fetchers/     # 适配器层（base + 注册表 + 各源实现）
│   ├── parse_input.py        # 输入路由
│   ├── render_battleplan.py  # 作战图渲染（xlsx + md）
│   ├── word_frequency.py     # 词频统计（词根分类辅助）
│   └── validate_keywords.py  # 词库完整性校验
├── evals/                    # 测试用例
├── examples/                 # 示范产出
└── output/                   # 每次运行的作战图落盘
```

## 🏠 交流社区

<div align="center">

🎯 **更多 AI 实战教程和专属福利尽在我们「MBG 跨境AI实战圈」,已有 50+ 跨境大卖、AI 专家热聊中**

—— 欢迎跨境电商从业者加入我们,一起探索 AI+商业的最佳实践和真实边界,跑通【跨境AI】的从 0 到 1,打败你的同事,干掉你的老板。

**社区介绍:[mp.weixin.qq.com/s/dOz4fLmRnaFR7sD_TQm00Q](https://mp.weixin.qq.com/s/dOz4fLmRnaFR7sD_TQm00Q)**

<img width="1125" height="618" alt="image" src="https://github.com/user-attachments/assets/20f47cd6-e33c-4f3e-9362-3846c11135fd" />

</div>

## 📜 License

MIT License — Copyright (c) 2026 Buluu@新西楼.AI

## 📖 写在最后

<div align="center">

**如果这个工具帮到了你,欢迎 ⭐ Star 支持。更多 AI × 跨境电商实操内容,关注公众号「新西楼.AI」。**

</div>
