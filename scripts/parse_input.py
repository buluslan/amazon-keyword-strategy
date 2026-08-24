"""输入路由 + 标准化。

两条输入路径最终都产出通用 schema 的 list[dict]：
1. 文件源 → fetch_from_file(filepath) 自动探测适配器（sif_xlsx/csv）解析
2. MCP 源 → Agent 按 SKILL.md 调 MCP 拿原始数据 → normalize_to_schema() 标准化

normalize_to_schema 识别字段名变体（驼峰/下划线/中文），映射到通用 schema。
字段缺失的 key 不凭空造——缺 key 才是缺失（填 0 是真实值）。
"""

import argparse
import copy
import json
import logging
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

# 兼容直接运行 / 模块导入
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from keyword_fetchers import detect_file_fetcher  # noqa: E402

logger = logging.getLogger(__name__)


def _to_int(val) -> Optional[int]:
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def _to_float(val) -> Optional[float]:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


# 字段别名表：归一化 key（lowercase + 去空格去连字符）→ (通用字段, 竞争子键 or None)
ALIASES = {
    # keyword
    "keyword": ("keyword", None), "关键词": ("keyword", None), "kw": ("keyword", None),
    "term": ("keyword", None), "searchterm": ("keyword", None), "搜索词": ("keyword", None),
    # search_volume
    "searches": ("search_volume", None), "searchvolume": ("search_volume", None),
    "搜索量": ("search_volume", None), "月搜索量": ("search_volume", None),
    "周搜索量": ("search_volume", None), "volume": ("search_volume", None),
    # aba_rank
    "searchesrank": ("aba_rank", None), "abarank": ("aba_rank", None),
    "aba": ("aba_rank", None), "aba排名": ("aba_rank", None),
    "searchrank": ("aba_rank", None), "rank": ("aba_rank", None),
    # bid
    "bid": ("bid", None), "竞价": ("bid", None), "cpc": ("bid", None),
    "建议竞价": ("bid", None), "ppc竞价": ("bid", None),
    # conversion_rate
    "purchaserate": ("conversion_rate", None), "conversionrate": ("conversion_rate", None),
    "转化率": ("conversion_rate", None), "购买率": ("conversion_rate", None),
    "conversion": ("conversion_rate", None),
    "24h点击转化率": ("conversion_rate", None),
    "24h归因的点击转化率": ("conversion_rate", None),
    "purchases": ("purchases", None), "月购买量": ("purchases", None), "购买量": ("purchases", None),
    "conversiontype": ("conversion_tag", None), "conversion_type": ("conversion_tag", None),
    "转化标签": ("conversion_tag", None),
    # trend
    "trend": ("trend", None), "趋势": ("trend", None), "growth": ("trend", None),
    "overall_trend": ("trend", None), "增长率": ("trend", None),
    # competition 子字段
    "monopolyclickrate": ("competition", "click_concentration"),
    "click_share": ("competition", "click_concentration"),
    "top3_click_share": ("competition", "click_concentration"),
    "top3clickingrate": ("competition", "click_concentration"),
    "top3conversionrate": ("competition", "conv_concentration"),
    "spr": ("competition", "spr"),
    "products": ("competition", "products"), "商品数": ("competition", "products"),
    "supplydemandratio": ("competition", "supply_demand_ratio"),
    "供需比": ("competition", "supply_demand_ratio"),
    "adproducts": ("competition", "ad_products"), "广告竞品数": ("competition", "ad_products"),
    "latest1daysads": ("competition", "ad_products"),
    "coverage_ratio": ("competition", "coverage"),
    "top3_conversion_share": ("competition", "conv_concentration"),
    # 结构性字段直通（幂等：已标准化的数据二次过 normalize 不丢来源）
    "sourceasin": ("source_asin", None),
}


def _map_field(key: str) -> Tuple[Optional[str], Optional[str]]:
    """识别字段名变体，返回 (通用字段, 竞争子键 or None)。未识别返回 (None, None)。"""
    k = str(key).strip().lower().replace("-", "").replace(" ", "").replace("_", "")
    if k in ALIASES:
        return ALIASES[k]
    # 原文中文包含兜底
    h = str(key)
    if "点击集中" in h or "click_share" in k:
        return ("competition", "click_concentration")
    if "转化集中" in h:
        return ("competition", "conv_concentration")
    if "商品数" in h:
        return ("competition", "products")
    if "供需" in h:
        return ("competition", "supply_demand_ratio")
    if "集中度" in h:
        return ("competition", "click_concentration")
    return (None, None)


def extract_asins(text: str) -> List[str]:
    """从任意文本中提取全部 ASIN（B0 开头 10 位字母数字），按出现顺序去重。

    多竞品输入用：用户给"B0XXX、B0YYY"或一段含多个 ASIN 的描述，Agent 拿到清单后
    逐个反查合并。哪个是本品由 Step 0 声明（用户说明/上下文），不由本函数判断。
    """
    if not text:
        return []
    seen: Dict[str, None] = {}
    for m in re.finditer(r"\b(B0[0-9A-Z]{8})\b", str(text).upper()):
        seen.setdefault(m.group(1), None)
    return list(seen.keys())


def _norm_source_asin(val) -> List[str]:
    """source_asin 归一：str/list 均可，逐元素 upper、去空、去重保序。

    大小写不归一会虚增竞品覆盖数（B0AAA 与 b0aaa 计 2 次），数组长度语义见
    adapter-interface.md §五·五。
    """
    if val is None:
        return []
    vals = val if isinstance(val, list) else [val]
    seen: Dict[str, None] = {}
    for a in vals:
        if a is None or a == "":
            continue
        s = str(a).strip().upper()
        if s:
            seen.setdefault(s, None)
    return list(seen.keys())


def normalize_to_schema(raw_items: List[Dict], source: str = "mcp",
                        source_asin=None) -> List[Dict]:
    """把任意来源的原始关键词数据映射到通用 schema。

    供 Agent 调 MCP（如 traffic_keyword）后用：拿到原始字段，传给本函数标准化。
    识别字段名变体（驼峰/下划线/中文），字段缺失的 key 不凭空造。

    Args:
        raw_items: 原始数据 list[dict]（如 MCP 返回的每条记录）
        source: 数据来源标识（写入 _source，用于作战图注明）
        source_asin: 本批数据来自哪个 ASIN 的反查（多竞品场景逐批传入，str/list 均可）。
            写入每条的 source_asin（数组）；同一词被多个竞品反查到时，
            由 dedup() 合并成多元素数组 = 词的竞品覆盖数。词表输入不传则不写 key。

    Returns:
        通用 schema list[dict]，每个至少含 keyword。
    """
    results: List[Dict] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        item: Dict = {}
        for k, v in raw.items():
            if v is None or v == "":
                continue
            field, sub = _map_field(k)
            if field == "keyword":
                item["keyword"] = str(v).strip()
            elif field == "search_volume":
                item["search_volume"] = _to_int(v)
            elif field == "aba_rank":
                item["aba_rank"] = _to_int(v)
            elif field == "bid":
                item["bid"] = _to_float(v)
            elif field == "conversion_rate":
                item["conversion_rate"] = _to_float(v)
            elif field == "purchases":
                item["purchases"] = _to_int(v)
            elif field == "conversion_tag":
                item["conversion_tag"] = str(v)
            elif field == "trend":
                item["trend"] = str(v)
            elif field == "source_asin":
                srcs = _norm_source_asin(v)
                if srcs:
                    item["source_asin"] = _norm_source_asin((item.get("source_asin") or []) + srcs)
            elif field == "competition":
                item.setdefault("competition", {})[sub] = _to_float(v)
        if item.get("keyword"):
            item["_source"] = source
            srcs = _norm_source_asin(source_asin)
            if srcs:
                item["source_asin"] = _norm_source_asin((item.get("source_asin") or []) + srcs)
            results.append(item)
    logger.info("normalize_to_schema：%d 条原始 → %d 条标准化（source=%s%s）",
                len(raw_items), len(results), source,
                f"，source_asin={source_asin}" if source_asin else "")
    return results


def fetch_from_file(filepath: str) -> List[Dict]:
    """自动探测文件适配器并解析，返回通用 schema 词表。

    Args:
        filepath: 词表文件路径（.xlsx/.xls/.csv/.txt）

    Returns:
        通用 schema list[dict]。文件不可识别返回空列表。
    """
    fetcher = detect_file_fetcher(filepath)
    if fetcher is None:
        logger.warning("无法识别文件格式：%s（支持 xlsx/csv/txt）", filepath)
        return []
    return fetcher.fetch(filepath=filepath)


def _merge_dict(dst: Dict, src: Dict) -> None:
    """递归子键合并：src 非空值补进 dst 空位，不覆盖已有值。

    跨源合并时 dict 型字段（competition/relevance 等）按子键互补——
    整字典先到先得会丢掉后批独有的子字段（如批A只有集中度、批B只有 SPR）。
    """
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge_dict(dst[k], v)
        elif v is not None and v != "" and dst.get(k) in (None, ""):
            dst[k] = copy.deepcopy(v)


def dedup(keywords: List[Dict]) -> List[Dict]:
    """同词合并去重（取最优字段——有值优先于无值）。

    多源/多竞品数据合并到同一行时用：同 keyword 只保留一行，顶层字段取首个非空值，
    dict 型字段（competition 等）递归子键互补；source_asin（反查来源数组）按批拼接
    去重（元素统一 upper）——数组长度 = 该词被几个反查 ASIN 命中（竞品覆盖数）。
    """
    merged: Dict[str, Dict] = {}
    for kw in keywords:
        if not isinstance(kw, dict):
            continue
        raw = kw.get("keyword")
        kstr = str(raw).strip() if raw is not None else ""
        key = kstr.lower()
        if not key:
            continue
        row = copy.deepcopy(kw)
        row["keyword"] = kstr
        if key not in merged:
            merged[key] = row
            continue
        existing = merged[key]
        for k, v in row.items():
            if k in ("keyword", "_source", "source_asin"):
                continue
            if isinstance(v, dict):
                if isinstance(existing.get(k), dict):
                    _merge_dict(existing[k], v)
                elif existing.get(k) in (None, ""):
                    existing[k] = copy.deepcopy(v)
            elif v is not None and v != "" and (existing.get(k) in (None, "")):
                existing[k] = v
        src_new = _norm_source_asin(kw.get("source_asin"))
        if src_new:
            combined = _norm_source_asin((existing.get("source_asin") or []) + src_new)
            existing["source_asin"] = combined
    return list(merged.values())


def main():
    parser = argparse.ArgumentParser(description="解析词表文件 → 通用 schema JSON")
    parser.add_argument("--filepath", required=True, help="词表文件路径（xlsx/csv/txt）")
    parser.add_argument("--out", default=None, help="输出 JSON 路径（默认 stdout）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    keywords = fetch_from_file(args.filepath)
    keywords = dedup(keywords)
    payload = {
        "filepath": args.filepath,
        "count": len(keywords),
        "fields_available": _available_fields(keywords),
        "keywords": keywords,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"✅ {len(keywords)} 词 → {args.out}")
    else:
        print(text)


def _available_fields(keywords: List[Dict]) -> List[str]:
    """统计词表中出现过的通用字段（非 _ 开头）。"""
    fields = set()
    for kw in keywords:
        for k in kw:
            if not k.startswith("_"):
                fields.add(k)
    return sorted(fields)


if __name__ == "__main__":
    main()
