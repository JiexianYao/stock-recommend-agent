"""联网搜索工具 —— Tavily Search API。"""
import httpx
from src.utils import config


class SearchError(Exception):
    """搜索功能异常。"""
    pass


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    执行联网搜索，返回结果列表。
    每条结果: {"title": str, "url": str, "snippet": str}
    """
    if not config.TAVILY_API_KEY:
        raise SearchError(
            "联网搜索功能不可用: TAVILY_API_KEY 为空。"
            "请在 .env 中配置 TAVILY_API_KEY，或前往 https://tavily.com 获取 API Key。"
        )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": config.TAVILY_API_KEY,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
            },
            timeout=15,
        )
        data = resp.json()
        return [
            {"title": r["title"], "url": r["url"], "snippet": r["content"]}
            for r in data.get("results", [])
        ]
