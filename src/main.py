"""入口文件 —— 启动金融荐股 Agent。"""
import asyncio
from src.utils import config
from src.agent import StockAgent


async def main():
    provider = "Google Gemini" if config.LLM_PROVIDER == "gemini" else "OpenAI"
    model = config.GEMINI_MODEL if config.LLM_PROVIDER == "gemini" else config.OPENAI_MODEL

    print("=" * 55)
    print(f"  StockAgent - 金融荐股智能体")
    print(f"  LLM: {provider} ({model})")
    print(f"  输入 'quit' 退出")
    print("=" * 55)

    agent = StockAgent()

    while True:
        try:
            user_input = input("\n请输入您的需求: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        print("\n[Agent 思考中...]\n")
        result = await agent.run(user_input)
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
