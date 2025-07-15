import os
import uuid
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Literal, Optional, Union
from openai import OpenAI
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from rich import print
import uvicorn

load_dotenv()
app = FastAPI()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

# ---- Models ----

class ContentBlock(BaseModel):
    type: Literal["text"]
    text: str

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: Union[str, List[ContentBlock]]

class MessagesRequest(BaseModel):
    model: str = "claude-3-opus"
    messages: List[Message]
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False

# ---- Helper ----

def anthropic_to_openai(messages: List[Message]) -> List[dict]:
    """Flatten Anthropic-style content blocks into OpenAI-style messages."""
    converted = []
    for m in messages:
        if isinstance(m.content, str):
            content_str = m.content
        else:
            content_str = "\n\n".join(block.text for block in m.content if block.type == "text")
        converted.append({"role": m.role, "content": content_str})
    return converted

# ---- Endpoint ----

@app.post("/v1/messages")
async def proxy(request: MessagesRequest):
    print(f"[bold cyan]🛰️  Proxying to Groq: {request.model}[/bold cyan]")

    chat_messages = anthropic_to_openai(request.messages)

    if request.stream:
        def stream_response():
            chat = client.chat.completions.create(
                model="moonshotai/kimi-k2-instruct",
                messages=chat_messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )
            for chunk in chat:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta

        return StreamingResponse(stream_response(), media_type="text/plain")

    else:
        chat = client.chat.completions.create(
            model="moonshotai/kimi-k2-instruct",
            messages=chat_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        return {
            "id": f"msg_{uuid.uuid4().hex}",
            "model": f"groq/llama3-70b-8192",
            "role": "assistant",
            "type": "message",
            "content": [{"type": "text", "text": chat.choices[0].message.content}],
            "usage": {
                "input_tokens": chat.usage.prompt_tokens,
                "output_tokens": chat.usage.completion_tokens,
            },
            "stop_reason": "end_turn",
            "stop_sequence": None,
        }

@app.get("/")
def root():
    return {"message": "Groq Anthropic Proxy is up 🚀"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7187)