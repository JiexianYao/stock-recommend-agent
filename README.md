# StockAgent - 金融荐股智能体

基于 **LLM Function Calling** 的金融荐股系统。上游接收用户自然语言查询，Agent 自主决定搜索策略、调用联网搜索获取权威数据做背书，下游输出结构化荐股结果（六位股票代码 + 分析推理）。

> 支持 **Google Gemini** / **OpenAI**，在 `.env` 里一行切换，默认 Gemini。

## 什么是 Agent？为什么不用 OpenClaw？

"Agent"本质上是一种**设计模式**，不是某个具体框架：

```
硬编码流水线:    搜索 → 提取 → 分析    (写死的，不论用户问什么都一样跑)
Agent 模式:      LLM 自己决定要不要搜 → 搜什么关键词 → 结果够不够 → 不够再搜？
```

这个项目的 Agent 核心就 **80 行代码**（[src/agent.py](src/agent.py)），直接用 LLM 的 function calling 实现：

```
用户输入 → LLM(带 tools 定义)
              ├─ 需要调工具? → 执行搜索 → 结果回传 LLM → 综合输出
              └─ 不需要? → 直接回复
```

**不需要 OpenClaw、LangChain 等任何框架**。OpenClaw 只是实验室统一选型，你导师要的是 Function Calling 这个模式，用啥实现都一样。

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                      用户 (User)                         │
│              "推荐一支新能源龙头股"                         │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                  StockAgent (80行)                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │           LLM (Gemini / OpenAI)                     │  │
│  │  意图解析 → 搜索策略规划 → 数据综合 → 荐股输出      │  │
│  └──────────────────────┬─────────────────────────────┘  │
│                         │  function_calls                 │
│         ┌───────────────┼───────────────┐               │
│         ▼               ▼               ▼                │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │   Search   │  │  Extract   │  │  Analyze   │        │
│  │   Skill    │  │   Skill    │  │   Skill    │        │
│  │ (联网搜索) │  │ (数据提取) │  │ (荐股分析) │        │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘        │
└────────┼───────────────┼───────────────┼────────────────┘
         │               │               │
         ▼               ▼               ▼
┌──────────────────────────────────────────────────────────┐
│               外部权威数据源 (Data Sources)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  Tavily Search API  │  │ 东方财富 │  ...          │
│  │  Search  │  │ (免费)    │  │   RSS    │               │
│  └──────────┘  └──────────┘  └──────────┘               │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│                    输出 (Structured Output)               │
│  {                                                       │
│    "stock_code": "300750",                               │
│    "stock_name": "宁德时代",                               │
│    "recommendation": "推荐",                              │
│    "reasoning": "Q3净利润+26%, 全球市占率37%...",         │
│    "sources": ["eastmoney.com/...", "sina.com/..."]      │
│  }                                                       │
└──────────────────────────────────────────────────────────┘
```

### LLM 适配层

`src/llm.py` 封装了 Gemini 和 OpenAI 的差异，对外暴露统一接口：

```
agent.py  ──→  chat(messages, tools) ──┬── _chat_gemini()  (默认)
                                        └── _chat_openai()
```

`.env` 里改一行切换：

```env
LLM_PROVIDER=gemini   # 或 openai
```

## 项目目录结构

```
stockagent/
├── README.md
├── requirements.txt
├── .env                        # API Key 配置 (已包含在仓库)
│
├── src/
│   ├── main.py                 # CLI 入口
│   ├── agent.py                # Agent 核心循环 (80行，零框架)
│   ├── llm.py                  # LLM 适配层 (Gemini / OpenAI)
│   │
│   ├── skills/                 # 技能模块
│   │   ├── search.py           # 搜索 Skill (构造搜索词 + 调用搜索)
│   │   ├── extract.py          # 提取 Skill (搜索结果 → 结构化数据)
│   │   └── analyze.py          # 分析 Skill (综合数据 → 荐股结论)
│   │
│   ├── tools/                  # 底层工具
│   │   └── web_search.py       # 搜索API封装 (Tavily)
│   │
│   └── utils/
│       └── config.py           # 环境变量加载
│
└── tests/
    └── test_with_mock.py       # Mock 集成测试 (5个，全部通过)
```

## 快速开始

### 1. 安装

```bash
# Python 3.10+
pip install -r requirements.txt
```

### 2. 配置

编辑根目录 `.env`，填入你的 Gemini API Key（已有模板，改一行即可）：

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=你的真实Key
```

没 Gemini Key 也可以切换 OpenAI：

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
```

### 3. 运行

```bash
python src/main.py
```

### 4. 使用示例

```
请输入您的需求: 最近新能源板块有什么值得关注的股票？

[Agent 思考中...]

{
  "stock_code": "300750",
  "stock_name": "宁德时代",
  "recommendation": "推荐",
  "reasoning": "2024Q3净利润同比增长26.4%，动力电池全球市占率37%...",
  "sources": [
    "https://www.eastmoney.com/report/300750_q3_2024",
    "https://www.sina.com.cn/finance/new_energy_2024"
  ],
  "risk_note": "以上分析基于公开信息，不构成投资建议。"
}
```

## 设计要点

| 要点 | 说明 |
|------|------|
| **零框架依赖** | Agent 核心仅 80 行，纯 LLM function calling，不依赖任何 Agent 框架 |
| **LLM 只做推理** | LLM 不编造数据，只负责意图理解 + 搜索策略 + 综合推理 |
| **数据来自搜索** | 所有股票信息通过联网搜索实时获取，自带来源 URL |
| **可插拔 LLM** | `src/llm.py` 适配层，Gemini / OpenAI 一行切换 |
| **可插拔搜索** | `web_search.py` 封装 Tavily Search API，联网获取权威财经数据 |
| **Skills 解耦** | 搜索、提取、分析三个 Skill 独立，方便单独调试替换 |
| **优雅降级** | 搜索无结果时不崩溃，诚实说明数据不足 |

## 测试

```bash
PYTHONPATH=. python tests/test_with_mock.py
```

```
[Test 1] extract_skill — 股票代码提取正确 ✓
[Test 2] analyze_skill — 输出结构完整 ✓
[Test 3] Agent 全链路集成 — 完整链路跑通 ✓
[Test 4] Agent 直接回复 — LLM无需工具调用 ✓
[Test 5] 错误处理 — 搜索无结果时优雅降级 ✓
```

## 依赖项

```
openai>=1.0           # OpenAI SDK
google-genai>=1.0     # Gemini SDK
httpx>=0.25           # HTTP 客户端
python-dotenv>=1.0    # 环境变量
pydantic>=2.0         # 数据校验
```

## License

MIT
