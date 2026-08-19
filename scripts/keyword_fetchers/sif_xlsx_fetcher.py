"""SIF 网页导出 xlsx 适配器。

解析 SIF 关键词调研导出的 xlsx（含占位率/相关性等 SIF 独家字段），
模糊识别列名，映射到通用 schema。

实测字段（调研称 17 列，列名可能因版本略有变体，按包含关系匹配）：
关键词 / 中文翻译 / 相关性 / 相关性得分 / 周搜索量 / ABA排名 /
24h点击转化率 / 建议竞价(低/中/高) / Top3点击集中度 / Top3转化集中度 /
Top4/Top8/Top16/Top32/Top48 占位率。

注意：SIF xlsx 的搜索量是周维度，fetch 返回时标 _volume_period='week'，
分析层据此换算或标注口径差异。
"""

import logging
import os
from typing import Dict, List, Optional, Tuple

from .base import KeywordFetcher

logger = logging.getLogger(__name__)


def _to_int(val) -> Optional[int]:
    """安全转 int，失败返回 None。"""
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return None


def _to_float(val) -> Optional[float]:
    """安全转 float，失败返回 None。"""
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "").replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def _classify_column(header: str) -> Tuple[Optional[str], Optional[str]]:
    """模糊识别 SIF 列名，返回 (通用字段, 子键)。

    返回 (None, None) 表示透传列（如中文翻译）。
    顺序敏感：先匹配带后缀的（相关性得分 > 相关性，转化集中 > 转化）。
    """
    h = str(header).strip()
    hl = h.lower()
    if "关键词" in h or "keyword" in hl:
        return ("keyword", None)
    if "翻译" in h or "translation" in hl:
        return ("translation", None)
    if "相关性得分" in h or ("相关性" in h and "分" in h):
        return ("relevance", "score")
    if "相关性" in h or "relevant" in hl:
        return ("relevance", "tier")
    if "搜索量" in h or "searches" in hl or "search_volume" in hl:
        return ("search_volume", None)
    if "aba" in hl or "排名" in h:
        return ("aba_rank", None)
    if "转化集中" in h:
        return ("competition", "conv_concentration")
    if "点击集中" in h or "click_share" in hl:
        return ("competition", "click_concentration")
    if "转化" in h:
        return ("conversion_rate", None)
    if "竞价" in h or "bid" in hl:
        return ("bid", None)  # 具体 低/中/高 由表头判断
    if "top8" in hl:
        return ("relevance", "coverage_top8")
    if "top16" in hl:
        return ("relevance", "coverage_top16")
    if "top32" in hl:
        return ("relevance", "coverage_top32")
    if "top48" in hl:
        return ("relevance", "coverage_top48")
    if "占位" in h or "top4" in hl:
        return ("relevance", "coverage_top4")
    return (None, None)


def _bid_level(header: str) -> str:
    """从竞价列表头识别 低/中/高。"""
    h = str(header)
    if "高" in h or "high" in h.lower():
        return "高"
    if "低" in h or "low" in h.lower():
        return "低"
    return "中"


class SifXlsxFetcher(KeywordFetcher):
    """SIF 网页导出 xlsx 适配器。"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._filepath = self._config.get("filepath", "")

    def get_name(self) -> str:
        return "sif_xlsx"

    def list_fields(self) -> List[str]:
        return ["keyword", "search_volume", "aba_rank", "conversion_rate",
                "bid", "competition", "relevance"]

    def validate_config(self) -> bool:
        if not self._filepath or not os.path.isfile(self._filepath):
            return False
        if not self._filepath.lower().endswith((".xlsx", ".xls")):
            return False
        try:
            import openpyxl  # noqa: F401
            return True
        except ImportError:
            logger.warning("openpyxl 未安装，无法解析 xlsx")
            return False

    def fetch(self, asin: str = "", marketplace: str = "US", **kwargs) -> List[Dict]:
        filepath = kwargs.get("filepath", self._filepath)
        if not filepath:
            raise ValueError("SifXlsxFetcher 需要 filepath（config 或 kwargs）")
        import openpyxl

        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows:
            return []

        headers = [str(c) if c is not None else "" for c in rows[0]]
        col_map = []  # [(idx, field, sub_key, raw_header)]
        for idx, h in enumerate(headers):
            f, sk = _classify_column(h)
            if f:
                col_map.append((idx, f, sk, h))

        results: List[Dict] = []
        for row in rows[1:]:
            if not row or row[0] in (None, ""):
                continue
            item: Dict = {}
            bid_levels: Dict[str, float] = {}
            coverage: Dict[str, float] = {}
            for idx, field, sub, raw_h in col_map:
                val = row[idx] if idx < len(row) else None
                if val is None or val == "":
                    continue
                if field == "keyword":
                    item["keyword"] = str(val).strip()
                elif field == "translation":
                    item["_translation"] = str(val).strip()
                elif field == "search_volume":
                    item["search_volume"] = _to_int(val)
                    item["_volume_period"] = "week"  # SIF 周维度，分析层注意
                elif field == "aba_rank":
                    item["aba_rank"] = _to_int(val)
                elif field == "conversion_rate":
                    item["conversion_rate"] = _to_float(val)
                elif field == "competition":
                    item.setdefault("competition", {})
                    if sub:
                        item["competition"][sub] = _to_float(val)
                elif field == "bid":
                    level = _bid_level(raw_h)
                    v = _to_float(val)
                    if v is not None:
                        bid_levels[level] = v
                elif field == "relevance":
                    item.setdefault("relevance", {})
                    if sub == "tier":
                        item["relevance"]["tier"] = str(val).strip()
                    elif sub == "score":
                        item["relevance"]["score"] = _to_float(val)
                    elif sub and sub.startswith("coverage_top"):
                        n = sub.replace("coverage_top", "")
                        cv = _to_float(val)
                        if cv is not None:
                            coverage["top" + n] = cv
            # 竞价：优先取"中"，否则取均值
            if bid_levels:
                item["bid"] = bid_levels.get("中") or (
                    sum(bid_levels.values()) / len(bid_levels) if bid_levels else None
                )
            if coverage:
                item.setdefault("relevance", {})["coverage"] = coverage

            if item.get("keyword"):
                item["_source"] = "sif_xlsx"
                results.append(item)
        logger.info("SIF xlsx 解析完成：%d 词，源=%s", len(results), filepath)
        return results
