"""
关键词数据源适配器抽象基类

所有数据源适配器（SIF xlsx / CSV / 未来扩展源）继承此基类。
分析层只认通用 schema，不感知具体数据来源——加新源不改分析层。

设计约定（钉死）：
- fetch() 返回 list[dict]，每 dict 一个关键词，字段对齐通用 schema
- 字段缺失的 key 不要凭空造，直接缺（缺 key 才是缺失，填 0 是真实值不是缺失）
- 异常在 validate_config 拦截；fetch 自身不吞错，交给上层统一降级
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class KeywordFetcher(ABC):
    """关键词数据源适配器抽象基类。

    子类必须实现: fetch / list_fields / validate_config / get_name
    """

    def __init__(self, config: Optional[Dict] = None):
        """初始化适配器。

        Args:
            config: 可选配置字典（文件路径、凭证、源特定参数）
        """
        self._config = config or {}

    @abstractmethod
    def fetch(self, asin: str = "", marketplace: str = "US", **kwargs) -> List[Dict]:
        """获取关键词数据，返回通用 schema 的词表。

        Args:
            asin: Amazon ASIN（文件源可为空，用文件名标识）
            marketplace: 站点代码，默认 US
            **kwargs: 源特定参数（如 filepath）

        Returns:
            list[dict]，每个 dict 至少含 'keyword' 键，其他字段按源能力给。
            字段缺失的 key 不要凭空造——缺 key 才是缺失。
        """

    @abstractmethod
    def list_fields(self) -> List[str]:
        """声明本源能提供的通用 schema 字段名。

        分析层据此决定哪些增强逻辑可跑、哪些标 [缺失]。
        """

    @abstractmethod
    def validate_config(self) -> bool:
        """探测本源在当前环境是否可用（文件可读 / 凭证有效）。

        Returns:
            True 可用 / False 不可用。不抛异常——失败由上层走降级。
        """

    @abstractmethod
    def get_name(self) -> str:
        """返回源标识（如 'sif_xlsx'），用于日志和作战图注明数据来源。"""

    def get_config(self) -> Dict:
        """获取当前配置（只读副本）。"""
        return dict(self._config)

    def update_config(self, updates: Dict) -> None:
        """更新配置参数。"""
        self._config.update(updates)
