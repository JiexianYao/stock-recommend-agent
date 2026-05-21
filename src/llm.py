"""
LLM 适配层 —— 封装 OpenAI / Gemini 差异，提供统一接口。

只用这个模块的一个函数:
    chat(messages, tools) → LLMResponse

用法:
    from src.llm import chat, LLMResponse, ToolCall
    response = chat(messages, tools)
    if response.tool_calls:
        ... # 执行工具
    else:
        print(response.text)
"""
from dataclasses import dataclass, field
import json
from src.utils import config


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    text: str | None = None
    tool_calls: list[ToolCall] | None = None


def _convert_tools_openai_to_gemini(tools: list[dict]) -> list[dict]:
    """OpenAI tool 格式 → Gemini tool 格式"""
    declarations = []
    for t in tools:
        func = t["function"]
        params = func["parameters"]
        # Gemini 要求 type 大写
        gemini_params = {
            "type": "OBJECT",
            "properties": {},
            "required": params.get("required", []),
        }
        for name, prop in params.get("properties", {}).items():
            gemini_params["properties"][name] = {
                "type": prop["type"].upper(),
                "description": prop.get("description", ""),
            }
        declarations.append({
            "name": func["name"],
            "description": func.get("description", ""),
            "parameters": gemini_params,
        })
    return [{"function_declarations": declarations}]


def _convert_messages_openai_to_gemini(messages: list[dict]) -> tuple[str, list]:
    """从 OpenAI 格式提取 system prompt，转换历史消息为 Gemini 格式。"""
    system_prompt = ""
    gemini_history = []

    for m in messages:
        role = m["role"]
        content = m.get("content") or ""

        if role == "system":
            system_prompt = content
        elif role == "user":
            gemini_history.append({"role": "user", "parts": [content]})
        elif role == "assistant":
            parts = []
            if content:
                parts.append(content)
            # 转换 tool_calls → function_call parts
            for tc in m.get("tool_calls", []):
                func = tc["function"]
                parts.append({
                    "function_call": {
                        "name": func["name"],
                        "args": json.loads(func["arguments"]),
                    }
                })
            gemini_history.append({"role": "model", "parts": parts})
        elif role == "tool":
            # Gemini 的 function response 格式
            gemini_history.append({
                "role": "function",
                "parts": [{
                    "function_response": {
                        "name": "search_finance_info",
                        "response": {"content": content},
                    }
                }]
            })

    return system_prompt, gemini_history


# ── OpenAI 实现 ──

def _chat_openai(messages: list[dict], tools: list[dict]) -> LLMResponse:
    from openai import OpenAI

    client = OpenAI(
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
    )
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    msg = resp.choices[0].message

    if msg.tool_calls:
        return LLMResponse(tool_calls=[
            ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
            for tc in msg.tool_calls
        ])
    return LLMResponse(text=msg.content)


# ── Gemini 实现 ──

def _chat_gemini(messages: list[dict], tools: list[dict]) -> LLMResponse:
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)

    system_prompt, gemini_history = _convert_messages_openai_to_gemini(messages)
    gemini_tools = _convert_tools_openai_to_gemini(tools) if tools else None

    model = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL,
        system_instruction=system_prompt,
        tools=gemini_tools,
    )

    # 取最后一条用户消息作为新消息
    last_user_msg = messages[-1]["content"] if messages[-1]["role"] == "user" else ""

    # 用历史消息启动 chat
    if gemini_history:
        chat = model.start_chat(history=gemini_history[:-1])  # 除了最后一条
        response = chat.send_message(last_user_msg)
    else:
        response = model.generate_content(last_user_msg)

    # 解析响应
    if response.candidates and response.candidates[0].content.parts:
        tool_calls = []
        text_parts = []
        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                tool_calls.append(ToolCall(
                    id=f"gemini_{fc.name}",
                    name=fc.name,
                    arguments=dict(fc.args),
                ))
            elif hasattr(part, "text") and part.text:
                text_parts.append(part.text)

        if tool_calls:
            return LLMResponse(tool_calls=tool_calls)
        return LLMResponse(text="".join(text_parts))

    return LLMResponse(text=response.text if hasattr(response, "text") else "")


# ── 统一入口 ──

def chat(messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
    """统一的 LLM 调用接口，根据 config.LLM_PROVIDER 自动路由。"""
    if config.LLM_PROVIDER == "gemini":
        return _chat_gemini(messages, tools or [])
    else:
        return _chat_openai(messages, tools or [])
