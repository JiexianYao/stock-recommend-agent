"""提取 Skill —— 从搜索结果中提取结构化金融数据。"""

EXTRACT_SKILL_PROMPT = """你是一个金融数据提取专家。从搜索结果中提取关键信息：
- 股票代码（6位数字）
- 公司名称
- 关键财务指标（PE、市值、营收增长率等）
- 近期重大事件
- 行业地位

只提取搜索结果显示的信息，不要编造数据。"""


def extract_skill(search_results: list[dict], query_context: str) -> dict:
    """
    从搜索结果列表中提取结构化信息。
    返回: {"stock_code": str, "company": str, "metrics": dict, "events": list, "sources": list}
    """
    sources = [{"title": r["title"], "url": r.get("url", "")} for r in search_results]
    snippets = " ".join([r.get("snippet", "") for r in search_results])

    # 简易提取：找股票代码模式（6位数字）
    import re
    code_pattern = re.findall(r'\b(\d{6})\b', snippets)
    stock_code = code_pattern[0] if code_pattern else ""

    return {
        "stock_code": stock_code,
        "company": "",
        "metrics": {},
        "events": [],
        "snippets": [r.get("snippet", "") for r in search_results],
        "sources": sources,
    }
