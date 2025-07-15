"""Conversion utilities for transforming between API formats."""
import json
from typing import List, Dict, Any
from rich import print

from .models import Message, Tool


def convert_messages(messages: List[Message]) -> List[Dict[str, Any]]:
    """Convert Anthropic messages to OpenAI format."""
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


def convert_tools(tools: List[Tool]) -> List[Dict[str, Any]]:
    """Convert Anthropic tools to OpenAI format."""
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


def convert_tool_calls_to_anthropic(tool_calls) -> List[Dict[str, Any]]:
    """Convert OpenAI tool calls to Anthropic format."""
    content = []
    for call in tool_calls:
        fn = call.function
        arguments = json.loads(fn.arguments)

        print(f"[bold green]🛠 Tool Call: {fn.name}({json.dumps(arguments, indent=2)})[/bold green]")

        content.append(
            {"type": "tool_use", "id": call.id, "name": fn.name, "input": arguments}
        )
    return content