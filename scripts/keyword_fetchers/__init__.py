"""关键词数据源适配器包。

文件源（Python 直接解析）:
- SIF xlsx (SifXlsxFetcher) — SIF 网页导出，含占位率/相关性等独家字段
- CSV (CsvFetcher) — 通用 csv 词表（卖家精灵/H10/JS 导出或手动整理），普通用户主路径

⚠️ MCP 源（sellersprite / sif_mcp）不在此包：
MCP 工具是 Agent 工具，Python 不能直接调。MCP 路径由 SKILL.md 指引
Agent 调用，拿到原始数据后调 parse_input.normalize_to_schema() 标准化。

加新文件源 = 新建一个 fetcher 文件 + registry 加一行（见 adapter-interface.md §七）。
"""

from .base import KeywordFetcher
from .registry import (
    FETCHER_REGISTRY,
    detect_file_fetcher,
    get_fetcher,
    list_fetchers,
)

__all__ = [
    "KeywordFetcher",
    "FETCHER_REGISTRY",
    "get_fetcher",
    "detect_file_fetcher",
    "list_fetchers",
]
