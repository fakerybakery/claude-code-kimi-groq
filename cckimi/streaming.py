"""Streaming utilities for Server-Sent Events (SSE) support."""
import json
import uuid
from typing import Dict, Any, Iterator


def sse(event: str, data: Dict[str, Any]) -> str:
    """Encode one server-sent-event block."""
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


def anthropic_stream(
    groq_chunks: Iterator,
    usage_in: int,
    model_name: str,
) -> Iterator[bytes]:
    """Translate Groq's OpenAI chunks to Anthropic SSE format."""
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    
    # Send message start event
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

    # Send content block start event
    yield sse(
        "content_block_start",
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        },
    ).encode()

    # Process chunks and send deltas
    out_tokens = 0
    for chunk in groq_chunks:
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

    # Send completion events
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