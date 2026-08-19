"""数据源注册表 + 工厂。

文件源（Python 直接解析）注册在此。加新文件源 = 新建 fetcher 文件 + 这里加一行。
MCP 源（sellersprite / sif_mcp）不在 Python 适配器——MCP 是 Agent 工具，
Python 不能直接调；MCP 路径由 SKILL.md 指引 Agent 调用，拿到原始数据后
调 parse_input.normalize_to_schema() 标准化（见 adapter-interface.md §三）。
"""

import logging
from typing import Dict, List, Optional

from .base import KeywordFetcher
from .csv_fetcher import CsvFetcher
from .sif_xlsx_fetcher import SifXlsxFetcher

logger = logging.getLogger(__name__)

# 文件源注册表：名称 -> 实现类
FETCHER_REGISTRY: Dict[str, type] = {
    "sif_xlsx": SifXlsxFetcher,
    "csv": CsvFetcher,
}


def get_fetcher(name: str, **kwargs) -> KeywordFetcher:
    """按名称获取适配器实例。"""
    name = name.lower().strip()
    if name not in FETCHER_REGISTRY:
        raise ValueError(
            f"未知文件数据源: '{name}'，可选项: [{', '.join(FETCHER_REGISTRY)}]"
        )
    return FETCHER_REGISTRY[name](**kwargs)


def detect_file_fetcher(filepath: str) -> Optional[KeywordFetcher]:
    """按文件后缀自动选文件适配器，返回 validate_config 通过的实例。

    Args:
        filepath: 用户上传的词表文件路径

    Returns:
        可用的 fetcher 实例；无法识别返回 None。
    """
    ext = filepath.lower().rsplit(".", 1)[-1] if "." in filepath else ""
    candidates = []
    if ext in ("xlsx", "xls"):
        candidates.append("sif_xlsx")
    if ext in ("csv", "txt"):
        candidates.append("csv")
    # 都试一遍（sif_xlsx 也能解析通用 xlsx）
    if not candidates:
        candidates = ["sif_xlsx", "csv"]
    for name in candidates:
        try:
            f = get_fetcher(name, config={"filepath": filepath})
            if f.validate_config():
                return f
        except Exception as e:
            logger.debug("适配器 %s 不可用: %s", name, e)
    return None


def list_fetchers() -> List[dict]:
    """列出所有已注册适配器。"""
    result = []
    for name, cls in FETCHER_REGISTRY.items():
        try:
            inst = cls()
            result.append({
                "name": name,
                "display": inst.get_name(),
                "fields": inst.list_fields(),
            })
        except Exception:
            result.append({"name": name, "display": name, "fields": []})
    return result
