"""Pydantic models for API request/response schemas."""
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel


class ContentBlock(BaseModel):
    """Text content block in a message."""
    type: Literal["text"]
    text: str


class ToolUseBlock(BaseModel):
    """Tool use block in a message."""
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Union[str, int, float, bool, dict, list]]


class ToolResultBlock(BaseModel):
    """Tool result block in a message."""
    type: Literal["tool_result"]
    tool_use_id: str
    content: Union[str, List[Dict[str, Any]], Dict[str, Any], List[Any], Any]


class Message(BaseModel):
    """Message in a conversation."""
    role: Literal["user", "assistant"]
    content: Union[str, List[Union[ContentBlock, ToolUseBlock, ToolResultBlock]]]


class Tool(BaseModel):
    """Tool definition."""
    name: str
    description: Optional[str]
    input_schema: Dict[str, Any]


class MessagesRequest(BaseModel):
    """Request to create a message completion."""
    model: str
    messages: List[Message]
    max_tokens: Optional[int] = 1024
    temperature: Optional[float] = 0.7
    stream: Optional[bool] = False
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, Dict[str, str]]] = "auto"