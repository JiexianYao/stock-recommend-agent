"""联网搜索工具 —— 封装 Tavily Search API 或其他搜索后端。"""
import httpx
from src.utils import config


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    执行联网搜索，返回结果列表。
    每条结果: {"title": str, "url": str, "snippet": str}
    """
    # 如果有 Tavily API Key 就用 Tavily
    if config.TAVILY_API_KEY and "tvly" in config.TAVILY_API_KEY:
        return await _tavily_search(query, max_results)
    # 否则用免费的 DuckDuckGo (HTML scraping)
    return await _ddg_search(query, max_results)


async def _tavily_search(query: str, max_results: int) -> list[dict]:
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


async def _ddg_search(query: str, max_results: int) -> list[dict]:
    """DuckDuckGo 免费搜索（HTML 版，无需 API Key）。"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        # 简易 HTML 解析，提取搜索结果
        from html.parser import HTMLParser

        class DDGParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.results = []
                self.current = {}
                self.in_result = False
                self.in_snippet = False
                self.in_title = False
                self.capture = ""

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and "result__a" in attrs.get("class", ""):
                    self.in_title = True
                    self.current = {"url": attrs.get("href", "")}
                elif tag == "a" and "result__snippet" in attrs.get("class", ""):
                    self.in_snippet = True

            def handle_data(self, data):
                if self.in_title:
                    self.current["title"] = data.strip()
                elif self.in_snippet:
                    self.current["snippet"] = data.strip()

            def handle_endtag(self, tag):
                if self.in_title and tag == "a":
                    self.in_title = False
                elif self.in_snippet and tag == "a":
                    self.in_snippet = False
                    self.results.append(self.current)
                    self.current = {}

        parser = DDGParser()
        parser.feed(resp.text)
        return parser.results[:max_results]
