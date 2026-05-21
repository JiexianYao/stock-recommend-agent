"""搜索 Skill —— 根据查询意图构造搜索词，调用搜索工具获取权威信息。"""
from src.tools import web_search

SEARCH_SKILL_PROMPT = """你是一个金融信息搜索专家。根据用户的问题，提取2-3个核心搜索关键词，用中文搜索。
返回搜索结果中包含标题、URL和摘要。优先搜索权威财经来源（东方财富、新浪财经、同花顺、雪球等）。"""


async def search_skill(query: str) -> list[dict]:
    """
    根据用户查询意图，执行联网搜索。
    返回权威来源的搜索结果列表。
    """
    # 构造金融向的搜索词
    if "股票" in query or "股" in query or "推荐" in query:
        search_query = f"{query} 股票 分析 东方财富 site:eastmoney.com"
    else:
        search_query = f"{query} 股票 财经"

    results = await web_search(search_query, max_results=5)

    # 如果第一次没搜到足够结果，放宽再搜一次
    if len(results) < 2:
        results = await web_search(query + " 股票", max_results=5)

    return results
