"""词频统计 —— 辅助词根分类。

统计关键词中的 token（英文按空格分词，小写化）出现频率 + 共现，
供 Agent 识别共性/属性词根（高频且能自由组合的 token = 潜在词根）。

属基础层能力：只需 keyword 字段，数据源无关，永不停摆。
"""

import argparse
import json
import logging
import os
import sys
from collections import Counter
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def tokenize(keyword: str) -> List[str]:
    """英文按空格/连字符分词，小写化，去停用词和短数字。"""
    STOP = {
        "for", "and", "the", "with", "of", "in", "on", "to", "a", "an",
        "is", "it", "this", "that", "by", "as", "at", "or", "be",
    }
    raw = keyword.lower().replace("-", " ").replace("/", " ").split()
    tokens = []
    for t in raw:
        t = t.strip(".,;:()\"'")
        if not t or t in STOP:
            continue
        if t.isdigit() and len(t) < 4:  # 短数字（如尺寸 2、年份保留）
            continue
        tokens.append(t)
    return tokens


def word_frequency(keywords: List[Dict], top_n: int = 50) -> List[Dict]:
    """统计 token 频率，返回 top_n。

    按覆盖关键词数计（token 出现在多少个不同关键词里），不是 token 实例数。
    Returns:
        [{token, keywords_count, share, sample_keywords: [...]}, ...]
        share = 出现该 token 的关键词占总数比。
    """
    total = len(keywords)
    if total == 0:
        return []
    token_kw_count = Counter()
    token_samples: Dict[str, List[str]] = {}
    for kw in keywords:
        word = kw.get("keyword", "")
        if not word:
            continue
        toks = tokenize(word)
        for t in set(toks):  # set 去重：按覆盖关键词数计
            token_kw_count[t] += 1
        for t in toks:
            samples = token_samples.setdefault(t, [])
            if len(samples) < 3 and word not in samples:
                samples.append(word)

    result = []
    for token, cnt in token_kw_count.most_common(top_n):
        result.append({
            "token": token,
            "keywords_count": cnt,
            "share": round(cnt / total, 3),
            "sample_keywords": token_samples.get(token, [])[:3],
        })
    return result


def main():
    parser = argparse.ArgumentParser(description="词频统计")
    parser.add_argument("--in", dest="inp", required=True, help="输入 JSON（parse_input 输出的 keywords）")
    parser.add_argument("--top", type=int, default=50)
    args = parser.parse_args()
    with open(args.inp, "r", encoding="utf-8") as f:
        payload = json.load(f)
    keywords = payload.get("keywords", payload if isinstance(payload, list) else [])
    freq = word_frequency(keywords, args.top)
    print(json.dumps(freq, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
