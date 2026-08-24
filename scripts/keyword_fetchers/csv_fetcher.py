"""通用 CSV 词表适配器。

解析任意来源的 csv 词表（卖家精灵/Helium10/Jungle Scout 导出或手动整理），
模糊识别列名，映射到通用 schema。覆盖无 MCP / 无 SIF 的普通用户主路径。
"""

import csv
import logging
import os
from typing import Dict, List, Optional, Tuple

from .base import KeywordFetcher

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


def _classify_column(header: str) -> Tuple[Optional[str], Optional[str]]:
    """通用 csv 列名识别（中英文都认）。返回 (通用字段, 子键)。"""
    h = str(header).strip()
    hl = h.lower()
    if "关键词" in h or "keyword" in hl:
        return ("keyword", None)
    if "搜索量" in h or "searches" in hl or "search volume" in hl or "volume" in hl:
        return ("search_volume", None)
    if "aba" in hl or "排名" in h or "rank" in hl:
        return ("aba_rank", None)
    if "转化集中" in h:
        return ("competition", "conv_concentration")
    if "集中" in h or "monopoly" in hl or "click_share" in hl:
        return ("competition", "click_concentration")
    if "spr" in hl:
        return ("competition", "spr")
    if "商品数" in h or "products" in hl:
        return ("competition", "products")
    if "供需" in h or "supply" in hl:
        return ("competition", "supply_demand_ratio")
    if "竞价" in h or "bid" in hl or "cpc" in hl:
        return ("bid", None)
    if "purchase" in hl:  # 先于 conversion 分支：purchases/purchase_count 等列是购买数，不并入转化率
        return ("purchase_rate", None)
    if "转化" in h or "conversion" in hl:
        return ("conversion_rate", None)
    if "趋势" in h or "trend" in hl or "growth" in hl:
        return ("trend", None)
    return (None, None)


class CsvFetcher(KeywordFetcher):
    """通用 CSV 词表适配器。"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._filepath = self._config.get("filepath", "")

    def get_name(self) -> str:
        return "csv"

    def list_fields(self) -> List[str]:
        return ["keyword", "search_volume", "aba_rank", "conversion_rate",
                "bid", "competition", "trend"]

    def validate_config(self) -> bool:
        if not self._filepath or not os.path.isfile(self._filepath):
            return False
        return self._filepath.lower().endswith((".csv", ".txt"))

    def fetch(self, asin: str = "", marketplace: str = "US", **kwargs) -> List[Dict]:
        filepath = kwargs.get("filepath", self._filepath)
        if not filepath:
            raise ValueError("CsvFetcher 需要 filepath（config 或 kwargs）")

        results: List[Dict] = []
        # 尝试常见编码（utf-8-sig 兼容 BOM）
        for enc in ("utf-8-sig", "utf-8", "gbk"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"无法解码 csv：{filepath}（试过 utf-8/gbk）")

        if not rows:
            return []

        # 判断有无表头（首行是否含关键词类列名）
        first_row = [str(c).strip() for c in rows[0]]
        has_header = any(
            "关键词" in c or "keyword" in c.lower() for c in first_row if c
        )
        if has_header:
            headers = first_row
            data_rows = rows[1:]
        else:
            # 无表头：默认首列为关键词
            headers = ["keyword"] + [f"col{i}" for i in range(1, len(first_row))]
            data_rows = rows

        col_map = []  # [(idx, field, sub)]
        for idx, h in enumerate(headers):
            f, sk = _classify_column(h)
            if f:
                col_map.append((idx, f, sk))

        for row in data_rows:
            # 列数回读自检（防串列）：数据行列数多于表头时按表头截断，少于表头时缺口自然落 None
            if len(row) > len(headers):
                logger.warning("csv 行列数(%d)多于表头(%d)，已截断：%s", len(row), len(headers), row[:3])
                row = row[:len(headers)]
            if not row or not row[0].strip():
                continue
            item: Dict = {}
            for idx, field, sub in col_map:
                val = row[idx] if idx < len(row) else None
                if val is None or str(val).strip() == "":
                    continue
                if field == "keyword":
                    item["keyword"] = str(val).strip()
                elif field == "search_volume":
                    item["search_volume"] = _to_int(val)
                elif field == "aba_rank":
                    item["aba_rank"] = _to_int(val)
                elif field == "conversion_rate":
                    item["conversion_rate"] = _to_float(val)
                elif field == "bid":
                    item["bid"] = _to_float(val)
                elif field == "trend":
                    item["trend"] = str(val).strip()
                elif field == "competition":
                    item.setdefault("competition", {})[sub] = _to_float(val)
            if item.get("keyword"):
                item["_source"] = "csv"
                results.append(item)
        logger.info("CSV 解析完成：%d 词，源=%s", len(results), filepath)
        return results
