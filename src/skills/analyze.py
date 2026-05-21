"""分析 Skill —— 综合搜索结果和提取数据，生成荐股结论。"""

ANALYZE_SKILL_PROMPT = """你是一个资深股票分析师。根据提供的搜索数据，给出荐股建议。
规则：
1. 只依据提供的数据做分析，不要编造
2. 如果数据不足以推荐，诚实说明
3. 输出结构化结果：股票代码、推荐理由、风险提示、数据来源"""


def analyze_skill(extracted: dict, user_query: str) -> dict:
    """
    综合数据，生成结构化荐股结果。
    返回: {"stock_code": str, "recommendation": str, "reasoning": str,
           "risk_note": str, "sources": list}
    """
    stock_code = extracted.get("stock_code", "")
    snippets = extracted.get("snippets", [])
    sources = extracted.get("sources", [])

    has_data = len(snippets) > 0 and any(len(s) > 20 for s in snippets)

    return {
        "stock_code": stock_code,
        "recommendation": "持有" if has_data else "数据不足，无法判断",
        "reasoning": _build_reasoning(snippets, user_query),
        "risk_note": "以上分析基于公开搜索结果，不构成投资建议。股市有风险，投资需谨慎。",
        "sources": [s["url"] for s in sources if s.get("url")],
        "snippets": snippets,
    }


def _build_reasoning(snippets: list[str], query: str) -> str:
    """根据搜索摘要拼接推理简述。"""
    if not snippets:
        return f"关于「{query}」，目前未找到足够的权威信息，建议更换关键词或查询渠道。"
    combined = " ".join(snippets[:3])
    # 截断到合理长度
    return combined[:500] if len(combined) > 500 else combined
