"""
Mock 数据集成测试 —— 不依赖任何外部 API，用 mock 数据跑通全链路。

用法:  PYTHONPATH=. python tests/test_with_mock.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import patch, MagicMock
from src.llm import LLMResponse, ToolCall
from src.skills.extract import extract_skill
from src.skills.analyze import analyze_skill
from src.agent import StockAgent

# ── Mock 搜索结果 ──
MOCK_SEARCH_RESULTS = [
    {
        "title": "宁德时代(300750)2024年三季报：净利润同比增长26%，全球市占率37%",
        "url": "https://www.eastmoney.com/report/300750_q3_2024",
        "snippet": (
            "宁德时代(300750)发布2024年三季报，前三季度实现营收2947亿元，"
            "归母净利润360亿元，同比增长26.4%。动力电池全球装机量市占率达37%，"
            "稳居全球第一。储能业务收入同比增长55%，成为第二增长曲线。"
            "当前PE约18倍，处于历史估值低位。"
        ),
    },
    {
        "title": "新能源板块分析：政策利好持续释放，龙头估值修复可期",
        "url": "https://www.sina.com.cn/finance/new_energy_2024",
        "snippet": (
            "2024年新能源汽车渗透率突破45%，政策端持续推进充电桩建设和以旧换新补贴。"
            "机构普遍认为新能源板块估值已处于历史底部区间，"
            "宁德时代(300750)、比亚迪(002594)等龙头企业受益明显。"
        ),
    },
    {
        "title": "北向资金本周加仓新能源龙头，宁德时代获净买入超20亿",
        "url": "https://www.xueqiu.com/article/northbound_flow_2024",
        "snippet": (
            "本周北向资金净买入A股超100亿元，其中宁德时代(300750)获净买入23.5亿元，"
            "位列全市场第一。外资机构认为中国新能源产业链竞争优势明显，"
            "当前估值具有吸引力。"
        ),
    },
]


# ═══════════════════════════════════════════
# Test 1: extract_skill 单元测试
# ═══════════════════════════════════════════

def test_extract_skill():
    result = extract_skill(MOCK_SEARCH_RESULTS, "新能源龙头股推荐")
    assert result["stock_code"] == "300750", f"期望 300750，实际 {result['stock_code']}"
    assert len(result["snippets"]) == 3
    assert len(result["sources"]) == 3
    print("  [PASS] test_extract_skill — 股票代码提取正确, 3条snippet, 3个来源")


# ═══════════════════════════════════════════
# Test 2: analyze_skill 单元测试
# ═══════════════════════════════════════════

def test_analyze_skill():
    extracted = extract_skill(MOCK_SEARCH_RESULTS, "推荐新能源龙头股")
    result = analyze_skill(extracted, "推荐新能源龙头股")
    assert result["stock_code"] == "300750"
    assert result["recommendation"] == "持有"
    assert len(result["reasoning"]) > 50
    assert "风险" in result["risk_note"]
    assert len(result["sources"]) == 3
    print("  [PASS] test_analyze_skill — 输出结构完整")


# ═══════════════════════════════════════════
# Test 3: Agent 全链路集成测试 (Mock LLM)
# ═══════════════════════════════════════════

@patch("src.agent.search_skill")
@patch("src.agent.chat")
def test_agent_full_pipeline(mock_chat, mock_search_skill):
    """
    完整链路:
    用户输入 → Agent → LLM返回tool_call → search/extract/analyze → LLM返回结论
    """
    mock_search_skill.return_value = MOCK_SEARCH_RESULTS

    # LLM 第一轮: 返回 tool_call
    # LLM 第二轮: 返回最终结论
    final_output = json.dumps({
        "stock_code": "300750",
        "stock_name": "宁德时代",
        "recommendation": "推荐",
        "reasoning": "宁德时代2024Q3净利润同比增长26.4%，动力电池全球市占率37%稳居第一。",
        "sources": [
            "https://www.eastmoney.com/report/300750_q3_2024",
            "https://www.sina.com.cn/finance/new_energy_2024",
        ],
        "risk_note": "以上分析基于公开信息，不构成投资建议。股市有风险，投资需谨慎。",
    }, ensure_ascii=False)

    mock_chat.side_effect = [
        LLMResponse(tool_calls=[
            ToolCall(id="call_001", name="search_finance_info",
                     arguments={"query": "宁德时代 2024 Q3财报 股票分析"})
        ]),
        LLMResponse(text=final_output),
    ]

    agent = StockAgent()
    result = agent.run("推荐一支新能源龙头股")

    output = json.loads(result)
    assert output["stock_code"] == "300750"
    assert output["stock_name"] == "宁德时代"
    assert "风险" in output["risk_note"]
    assert mock_search_skill.called
    assert mock_chat.call_count == 2

    print(f"  最终输出: {output['stock_code']} {output['stock_name']} → {output['recommendation']}")
    print("  [PASS] test_agent_full_pipeline — 完整链路跑通")


# ═══════════════════════════════════════════
# Test 4: 错误处理 —— LLM 直接返回(不调工具)
# ═══════════════════════════════════════════

@patch("src.agent.chat")
def test_agent_direct_answer(mock_chat):
    """有些简单问题 LLM 直接回答，不需要搜索。"""
    mock_chat.return_value = LLMResponse(text="你好！请告诉我你想了解哪方面的股票信息？")

    agent = StockAgent()
    result = agent.run("你好")

    assert "你好" in result or "股票" in result
    assert mock_chat.call_count == 1, "简单回复只需1轮"
    print("  [PASS] test_agent_direct_answer — LLM直接回复无需工具调用")


# ═══════════════════════════════════════════
# Test 5: 搜索无结果时优雅降级
# ═══════════════════════════════════════════

def test_no_search_results():
    empty_results = []
    extracted = extract_skill(empty_results, "不存在的股票XYZ")
    result = analyze_skill(extracted, "不存在的股票XYZ")

    assert result["stock_code"] == ""
    assert result["recommendation"] == "数据不足，无法判断"
    assert "未找到" in result["reasoning"] or "不足" in result["reasoning"]
    print("  [PASS] test_no_search_results — 搜索无结果时优雅降级")


# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print("  StockAgent Mock 集成测试")
    print("=" * 55)
    print()

    print("[Test 1] extract_skill — 数据提取")
    test_extract_skill()

    print("\n[Test 2] analyze_skill — 分析推理")
    test_analyze_skill()

    print("\n[Test 3] Agent 全链路集成")
    test_agent_full_pipeline()

    print("\n[Test 4] Agent 直接回复")
    test_agent_direct_answer()

    print("\n[Test 5] 错误处理 — 无搜索结果")
    test_no_search_results()

    print("\n" + "=" * 55)
    print("  全部 5 个测试通过!")
    print("=" * 55)
