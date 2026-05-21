"""
轻量 Agent 核心 —— 零框架依赖，纯 LLM function calling 实现。

架构就是一个循环:
  LLM(用户消息 + tools定义)
    → 需要调工具? → 执行工具 → 结果回传 LLM
    → 不需要? → 直接输出结果

支持 Google Gemini / OpenAI，.env 里切换 LLM_PROVIDER。
"""
import json
from src.llm import chat
from src.skills.search import search_skill
from src.skills.extract import extract_skill
from src.skills.analyze import analyze_skill
from src.utils import config

# ── 工具定义 (OpenAI function calling 格式, llm.py 自动转换) ──
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_finance_info",
            "description": "联网搜索权威财经信息。当需要为荐股提供数据背书时调用此工具。"
                           "输入搜索关键词，返回相关权威来源的搜索结果（标题、URL、摘要）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，如'宁德时代 Q3财报 2024'或'新能源龙头股 PE 市值'",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

SYSTEM_PROMPT = """你是一个专业的金融荐股 Agent。你的任务是根据用户需求推荐股票并给出有数据支撑的分析。

## 工作流程
1. 理解用户的问题意图
2. 调用 `search_finance_info` 工具搜索权威财经信息为推荐做背书
3. 根据搜索结果，综合分析后给出荐股建议

## 输出格式
你必须输出如下结构的 JSON:
{
  "stock_code": "六位数字股票代码，如 300750，不确定则为空字符串",
  "stock_name": "股票名称",
  "recommendation": "推荐/持有/观望/卖出 之一",
  "reasoning": "推荐理由（基于搜索数据，200字以内）",
  "sources": ["数据来源URL列表"],
  "risk_note": "风险提示"
}

## 重要规则
- 只依据搜索到的数据做分析，不要编造任何数字
- 搜索结果不足时诚实说明，不要强行推荐
- 输出末尾加上风险提示
"""


class StockAgent:
    """轻量金融荐股 Agent —— 零框架依赖，80 行搞定。"""

    def run(self, user_message: str) -> str:
        """处理用户消息，返回荐股分析结果。"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        for _ in range(config.MAX_TOOL_ROUNDS):
            resp = chat(messages, TOOLS)

            # 没有 tool_calls —— LLM 直接返回了结果
            if not resp.tool_calls:
                return resp.text or "抱歉，未能生成分析结果。"

            # 有 tool_calls —— 执行工具并回传结果
            assistant_msg = {"role": "assistant", "content": resp.text, "tool_calls": []}
            for tc in resp.tool_calls:
                assistant_msg["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                })
            messages.append(assistant_msg)

            for tc in resp.tool_calls:
                if tc.name == "search_finance_info":
                    query = tc.arguments.get("query", user_message)
                    import asyncio
                    search_results = asyncio.run(search_skill(query))
                    extracted = extract_skill(search_results, query)
                    analysis = analyze_skill(extracted, user_message)
                    tool_result = json.dumps(analysis, ensure_ascii=False)
                else:
                    tool_result = json.dumps({"error": "unknown tool"}, ensure_ascii=False)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })

        return "Agent 超过最大循环轮次，请稍后重试。"
