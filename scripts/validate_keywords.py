"""词库完整性校验门。

校验通用 schema 词表的完整性，返回 exit code：
- 0 = 通过（有关键词，可跑分析）
- 1 = 警告（字段大面积缺失，降级运行但提醒 Agent）
- 2 = 错误（无关键词 / 格式错误，不能跑）

仿罗盘 preflight 校验门：Agent 跑分析前先校验，不通过 = 流程非法。
"""

import argparse
import json
import logging
import sys
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# 通用 schema 选填增强字段（缺失不致命，但大面积缺失要提醒）
ENHANCEMENT_FIELDS = ["search_volume", "aba_rank", "conversion_rate", "bid", "competition"]


def validate(keywords: List[Dict]) -> Tuple[int, List[str]]:
    """校验词表，返回 (exit_code, messages)。"""
    msgs: List[str] = []

    if not isinstance(keywords, list):
        return (2, ["❌ 词表不是 list 格式"])
    if len(keywords) == 0:
        return (2, ["❌ 词表为空，无法分析"])

    # 1. 必填 keyword 检查
    no_kw = [i for i, kw in enumerate(keywords) if not kw.get("keyword")]
    if no_kw:
        return (2, [f"❌ {len(no_kw)} 条记录缺 keyword（必填），请清洗后重跑"])

    # 2. 去重检查
    lower_kws = [str(kw.get("keyword", "")).strip().lower() for kw in keywords]
    dup = len(keywords) - len(set(lower_kws))
    if dup > 0:
        msgs.append(f"⚠️ {dup} 条重复关键词（建议先 dedup）")

    # 3. 增强字段缺失率（大面积缺失 = 降级提醒）
    n = len(keywords)
    for field in ENHANCEMENT_FIELDS:
        miss = sum(1 for kw in keywords if kw.get(field) in (None, "", {}))
        rate = miss / n
        if rate == 1.0:
            msgs.append(f"⏳ {field} 全缺失（基础层仍可跑，增强层标 [缺失]）")
        elif rate > 0.7:
            msgs.append(f"⚠️ {field} 缺失率 {rate:.0%}（增强分析将受限）")

    # 4. 数据诚实检查：不应有 0 冒充缺失（0 是真实值，但连续多个 0 可疑）
    zero_vol = sum(1 for kw in keywords if kw.get("search_volume") == 0)
    if zero_vol > n * 0.3:
        msgs.append(f"⚠️ {zero_vol} 条 search_volume=0，确认是真实值而非缺失冒充")

    code = 0 if not msgs else 1
    if code == 0:
        msgs.append(f"✅ 校验通过：{n} 词，增强字段覆盖良好")
    return (code, msgs)


def main():
    parser = argparse.ArgumentParser(description="词库完整性校验门")
    parser.add_argument("--in", dest="inp", required=True, help="输入 JSON（parse_input 输出）")
    parser.add_argument("--strict", action="store_true", help="严格模式：警告也当失败")
    args = parser.parse_args()
    with open(args.inp, "r", encoding="utf-8") as f:
        payload = json.load(f)
    keywords = payload.get("keywords", payload if isinstance(payload, list) else [])

    code, msgs = validate(keywords)
    for m in msgs:
        print(m)

    if args.strict and code == 1:
        code = 2
    sys.exit(code)


if __name__ == "__main__":
    main()
