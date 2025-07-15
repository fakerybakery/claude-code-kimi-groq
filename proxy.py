import asyncio
import json
import os
import uuid
from typing import Any, Dict, List, Literal, Optional, Union, AsyncIterator

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openai import OpenAI
from pydantic import BaseModel
from rich import print

load_dotenv()
app = FastAPI()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"
)

GROQ_MODEL = "moonshotai/kimi-k2-instruct"
GROQ_MAX_OUTPUT_TOKENS = 16_384     # max Groq supports

class ContentBlock(BaseModel):
    type: Literal["text"]
    text: str

class ToolUseBlock(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Union[str, int, float, bool, dict, list]]

class ToolResultBlock(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    content: Union[str, List[Dict[str, Any]], Dict[str, Any], List[Any], Any]

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: Union[str, List[Union[ContentBlock, ToolUseBlock, ToolResultBlock]]]

class Tool(BaseModel):
    name: str
    description: Optional[str]
    input_schema: Dict[str, Any]

class MessagesRequest(BaseModel):
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, Dict[str, str]]] = "auto"


def convert_messages(messages: List[Message]) -> List[dict]:
    converted = []
    for m in messages:
        if isinstance(m.content, str):
            content = m.content
        else:
            parts = []
            for block in m.content:
                if block.type == "text":
                    parts.append(block.text)
                elif block.type == "tool_use":
                    tool_info = f"[Tool Use: {block.name}] {json.dumps(block.input)}"
                    parts.append(tool_info)
                elif block.type == "tool_result":
                    result = block.content
                    print(f"[bold yellow]📥 Tool Result for {block.tool_use_id}: {json.dumps(result, indent=2)}[/bold yellow]")
                    parts.append(f"<tool_result>{json.dumps(result)}</tool_result>")
            content = "\n".join(parts)
        converted.append({"role": m.role, "content": content})
    return converted



def convert_tools(tools: List[Tool]) -> List[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.input_schema,
            },
        }
        for t in tools
    ]


def convert_tool_calls_to_anthropic(tool_calls) -> List[dict]:
    content = []
    for call in tool_calls:
        fn = call.function
        arguments = json.loads(fn.arguments)

        print(f"[bold green]🛠 Tool Call: {fn.name}({json.dumps(arguments, indent=2)})[/bold green]")

        content.append(
            {"type": "tool_use", "id": call.id, "name": fn.name, "input": arguments}
        )
    return content



# -------- NEW: 1️⃣ Anthropic‑style SSE helpers -----------
def sse(event: str, data: Dict[str, Any]) -> str:
    """Encode one server‑sent‑event block."""
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"

def anthropic_stream(
    groq_chunks,
    usage_in: int,
    model_name: str,
):
    """Translate Groq’s OpenAI chunks ➜ Anthropic SSE."""
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    yield sse(
        "message_start",
        {
            "type": "message_start",
            "message": {
                "id": msg_id,
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": model_name,
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": usage_in, "output_tokens": 0},
            },
        },
    ).encode()

    yield sse(
        "content_block_start",
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        },
    ).encode()

    out_tokens = 0
    for chunk in groq_chunks:    # not async!
        choice = chunk.choices[0]
        delta_text = getattr(choice.delta, "content", "") if hasattr(choice, "delta") else ""
        if delta_text:
            out_tokens += 1  # rough estimate
            yield sse(
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": delta_text},
                },
            ).encode()

        if getattr(choice, "finish_reason", None) is not None:
            break

    yield sse(
        "content_block_stop",
        {"type": "content_block_stop", "index": 0},
    ).encode()
    yield sse(
        "message_delta",
        {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": out_tokens},
        },
    ).encode()
    yield sse("message_stop", {"type": "message_stop"}).encode()


# -------- NEW: 2️⃣ Main route with streaming -----------
@app.post("/v1/messages")
async def proxy(request: MessagesRequest):
    print(f"[bold cyan]🚀 Anthropic → Groq | Model: {request.model}[/bold cyan]")

    openai_messages = convert_messages(request.messages)
    tools = convert_tools(request.tools) if request.tools else None
    max_tokens = min(request.max_tokens or GROQ_MAX_OUTPUT_TOKENS, GROQ_MAX_OUTPUT_TOKENS)

    if request.stream:
        # --- Streaming path ---
        groq_stream = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=openai_messages,
            tools=tools,
            tool_choice=request.tool_choice,
            temperature=request.temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        def streamer():
            # groq_stream is a regular iterator
            yield from anthropic_stream(
                groq_stream,
                usage_in=0,
                model_name=f"groq/{GROQ_MODEL}"
            )


        return StreamingResponse(streamer(), media_type="text/event-stream")

    # --- Non‑stream fallback (existing logic, shortened here) ---
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=openai_messages,
        tools=tools,
        tool_choice=request.tool_choice,
        temperature=request.temperature,
        max_tokens=max_tokens,
    )

    choice = completion.choices[0]
    msg = choice.message

    if msg.tool_calls:
        tool_content = convert_tool_calls_to_anthropic(msg.tool_calls)
        stop_reason = "tool_use"
    else:
        tool_content = [{"type": "text", "text": msg.content}]
        stop_reason = "end_turn"

    return JSONResponse(
        {
            "id": f"msg_{uuid.uuid4().hex[:12]}",
            "model": f"groq/{GROQ_MODEL}",
            "role": "assistant",
            "type": "message",
            "content": tool_content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {
                "input_tokens": completion.usage.prompt_tokens,
                "output_tokens": completion.usage.completion_tokens,
            },
        }
    )

# CLI entry point unchanged
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7187)
