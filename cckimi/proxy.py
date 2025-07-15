"""Main proxy server for translating Anthropic API to Groq API."""
import uuid
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from rich import print

from .config import get_groq_client, GROQ_MODEL, GROQ_MAX_OUTPUT_TOKENS
from .models import MessagesRequest
from .converters import convert_messages, convert_tools, convert_tool_calls_to_anthropic
from .streaming import anthropic_stream

# Initialize FastAPI app
app = FastAPI()

# Initialize Groq client
client = get_groq_client()


@app.post("/v1/messages")
async def proxy(request: MessagesRequest):
    """Proxy endpoint that translates Anthropic API calls to Groq API."""
    print(f"[bold cyan]🚀 Anthropic → Groq | Model: {request.model}[/bold cyan]")

    # Convert request data to Groq format
    openai_messages = convert_messages(request.messages)
    tools = convert_tools(request.tools) if request.tools else None
    max_tokens = min(request.max_tokens or GROQ_MAX_OUTPUT_TOKENS, GROQ_MAX_OUTPUT_TOKENS)

    if request.stream:
        # Streaming response
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
            """Generator for streaming response."""
            yield from anthropic_stream(
                groq_stream,
                usage_in=0,
                model_name=f"groq/{GROQ_MODEL}"
            )

        return StreamingResponse(streamer(), media_type="text/event-stream")

    # Non-streaming response
    try:
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

        # Handle tool calls or regular text response
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
    except Exception as e:
        print(f"[bold red]❌ Error calling Groq: {e}[/bold red]")
        return JSONResponse(
            {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": str(e)
                }
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7187)